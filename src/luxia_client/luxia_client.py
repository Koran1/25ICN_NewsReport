import requests
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

# 로거 설정

class LuxiaLLMClient:
    """Luxia Cloud LLM 클라이언트 (HTTP API 직접 호출)"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Luxia LLM 클라이언트 초기화
        
        Args:
            api_key (str, optional): API 키. None인 경우 환경 변수에서 로드
        """
        self.base_url = "https://bridge.luxiacloud.com/luxia/v1/chat"
        self.api_key = api_key or 'U2FsdGVkX19wZkHyPZhORgU1+RFLLNo3/0kOHPQ99Z4WscKbJVkD9IQYSITjUC3mQOMDFnN1VqE5+WbBfw5+BLR240UQf73U4IHC1eGYCm8A9WYDzQ/t9KqEdkXChLI2ChgZPssr2XalNrJPFjCHNJ1U++/Lto/NN0uFD5mCR6QwQN46uqAWI+v+6WpJqThpARgCo9tjdyyp5qWYMSa1sw=='
        self.model = "luxia3-llm-32b-0731"
        
        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }
        self.logger = logging.getLogger(__name__)
    
    def chat_completion(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> str:
        """
        채팅 완성 요청
        
        Args:
            messages (List[Dict[str, str]]): 메시지 리스트
            temperature (float): 창의성 조절 (0.0 ~ 1.0)
            
        Returns:
            str: LLM 응답 내용
        """
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,  # 스트리밍 비활성화
                "temperature": temperature,
                "max_completion_tokens": 2048,
                "top_p": 1,
                "frequency_penalty": 0.1
            }
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                return "응답을 받지 못했습니다."
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"LLM API 요청 오류: {e}")
            return f"API 요청 오류가 발생했습니다: {e}"
        except json.JSONDecodeError as e:
            self.logger.error(f"LLM 응답 파싱 오류: {e}")
            return f"응답 파싱 오류가 발생했습니다: {e}"
        except Exception as e:
            self.logger.error(f"LLM 요청 중 예상치 못한 오류: {e}")
            return f"오류가 발생했습니다: {e}"
    
    def convert_table_to_str(self, table_data: str) -> str:
        """
        HTML 테이블 데이터를 문자열로 변환
        
        Args:
            table_data (str): 테이블 데이터
            
        Returns:
            list[str]: 테이블 데이터를 서술형 리스트 타입으로 변환한 데이터 
        """
        system_prompt = f"""
당신은 HTML 테이블 데이터를 서술형 리스트 타입으로 변환하는 전문가입니다. 
데이터 값과 컬럼명을 조합하여 서술형 리스트 타입으로 변환해주세요.
병합된 테이블 데이터가 감지되는 경우 동일한 데이터로 처리해주세요.

테이블 데이터:
{table_data}

응답 형식:
1. 테이블 데이터를 서술형 리스트 타입으로 변환한 데이터

응답 예시:
[
"데이터1",
"데이터2",
]
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": table_data}
        ]
        
        response = self.chat_completion(messages, temperature=0.3)
        return response