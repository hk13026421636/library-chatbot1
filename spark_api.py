"""
讯飞星火大模型 API 接入模块
用途：当FAQ知识库匹配不到时，调用大模型进行兜底回答
申请地址：https://xinghuo.xfyun.cn  注册后在控制台创建应用获取Key
"""
import _thread as thread
import base64
import hashlib
import hmac
import json
import ssl
import time
from datetime import datetime
from time import mktime
from urllib.parse import urlencode, urlparse
from wsgiref.handlers import format_date_time

import websocket


class SparkAPI:
    """讯飞星火大模型 WebSocket API 封装"""

    def __init__(self, app_id, api_key, api_secret, model_version='v3.5'):
        self.app_id = app_id
        self.api_key = api_key
        self.api_secret = api_secret

        # 模型版本对应的URL和domain
        version_map = {
            'v1.5': ('wss://spark-api.xf-yun.com/v1.1/chat', 'lite'),
            'v2.0': ('wss://spark-api.xf-yun.com/v2.1/chat', 'generalv2'),
            'v3.0': ('wss://spark-api.xf-yun.com/v3.1/chat', 'generalv3'),
            'v3.5': ('wss://spark-api.xf-yun.com/v3.5/chat', 'generalv3.5'),
            'v4.0': ('wss://spark-api.xf-yun.com/v4.0/chat', 'generalv4.0'),
            'pro': ('wss://spark-api.xf-yun.com/v3.1/chat', 'generalv3'),
        }
        self.url, self.domain = version_map.get(model_version, version_map['v3.5'])

    def _create_url(self):
        """生成鉴权URL"""
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        parsed = urlparse(self.url)
        host = parsed.hostname
        path = parsed.path

        signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
        signature_sha = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_origin.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        signature = base64.b64encode(signature_sha).decode('utf-8')

        authorization_origin = (
            f'api_key="{self.api_key}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature}"'
        )
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode('utf-8')

        params = {
            "authorization": authorization,
            "date": date,
            "host": host
        }
        return self.url + '?' + urlencode(params)

    def chat(self, question, system_prompt=None, timeout=15):
        """
        发送问题并获取回答
        参数:
            question: 用户问题
            system_prompt: 系统提示词（可选）
            timeout: 超时秒数
        返回: 回答文本 或 None（失败时）
        """
        if not all([self.app_id, self.api_key, self.api_secret]):
            return None

        result = {'text': '', 'done': False, 'error': None}

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": question})

        request_data = {
            "header": {"app_id": self.app_id, "uid": "library_bot"},
            "parameter": {
                "chat": {
                    "domain": self.domain,
                    "temperature": 0.7,
                    "max_tokens": 512,
                }
            },
            "payload": {
                "message": {"text": messages}
            }
        }

        def on_message(ws, message):
            data = json.loads(message)
            code = data['header']['code']
            if code != 0:
                result['error'] = f"API错误 code={code}"
                result['done'] = True
                ws.close()
                return
            choices = data['payload']['choices']
            text_list = choices['text']
            for t in text_list:
                result['text'] += t.get('content', '')
            if choices.get('status') == 2:
                result['done'] = True
                ws.close()

        def on_error(ws, error):
            result['error'] = str(error)
            result['done'] = True

        def on_close(ws, close_status_code, close_msg):
            result['done'] = True

        def on_open(ws):
            def run():
                ws.send(json.dumps(request_data))
            thread.start_new_thread(run, ())

        try:
            auth_url = self._create_url()
            ws = websocket.WebSocketApp(
                auth_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open
            )

            # 在子线程中运行WebSocket
            ws_thread = thread.start_new_thread(
                ws.run_forever,
                (),
                {"sslopt": {"cert_reqs": ssl.CERT_NONE}}
            )

            # 等待结果
            start = time.time()
            while not result['done'] and (time.time() - start) < timeout:
                time.sleep(0.1)

            if result['error']:
                print(f"[星火API] 错误: {result['error']}")
                return None

            return result['text'].strip() if result['text'] else None

        except Exception as e:
            print(f"[星火API] 异常: {e}")
            return None


# ===================== 简易测试 =====================

if __name__ == '__main__':
    # 测试用 —— 替换为你自己的Key
    spark = SparkAPI(
        app_id='你的APPID',
        api_key='你的APIKey',
        api_secret='你的APISecret',
        model_version='v3.5'
    )

    answer = spark.chat(
        "图书馆的自习室一般几点开门？",
        system_prompt="你是一个高校图书馆的智能咨询助手，请用简洁友好的语气回答图书馆相关问题。"
    )
    print("回答:", answer)
