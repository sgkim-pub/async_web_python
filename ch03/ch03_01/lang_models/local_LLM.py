
# pip install wheel

# nvidia-smi
# nvcc --version

# pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu126
# https://pytorch.org/

# pip install huggingface-hub
# pip install transformers
# pip install accelerate

import os

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

###########################################
# LLM 클래스 정의
###########################################

class QueryEngine():
    def __init__(self):
        ##################################
        # 실행 환경 설정
        ##################################
        if torch.cuda.is_available():
            self.device = torch.device('cuda')
        else:
            if torch.backends.mps.is_available():
                self.device = torch.device('mps')   # metal performance shader of Apple Silicon 
            else:
                self.device = torch.device('cpu')

        print('local_LLM.py.QueryEngine.__init__().self.device:', self.device)

    def loadModel(self, modelId, saveModelAsFile):
        ''' Load model from saved file or download from huggingface-hub.'''

        savedModelPath = './savedModel/{}'.format(modelId)
        isMounted = os.path.exists(savedModelPath)

        if isMounted:
            print('Load model and tokenizer from files: {}'.format(savedModelPath))
            self.tokenizer = AutoTokenizer.from_pretrained(savedModelPath)            
            self.model = AutoModelForCausalLM.from_pretrained(savedModelPath)
        else:
            print('Load model from huggingface hub: {}'.format(modelId))
            self.tokenizer = AutoTokenizer.from_pretrained(modelId)
            self.model = AutoModelForCausalLM.from_pretrained(modelId)

            if saveModelAsFile:
                ##################################
                # 다운로드한 모델, 토크나이저를 파일로 저장
                ##################################
                savePath = './savedModel/{}'.format(modelId)
                self.model.save_pretrained(savePath)
                self.tokenizer.save_pretrained(savePath)
                print('Save model as file:{}'.format(savePath))
            else:
                pass

        self.model.to(self.device)

    def generateChatPrompt(self, query):
        '''input: query sentence. 
        output: formatted prompt. <|user|>{prompt}<|end|><|assistant|>'''

        description = '당신은 사용자의 질문에 답변하는 챗봇입니다.'

        sentence = [
            {"role": 'system', "content": description}
            , {"role": 'user', "content": query}
        ]

        chatPrompt = self.tokenizer.apply_chat_template(
            sentence, tokenize=False, add_generation_prompt=True
        )

        print('local_LLM.py.QueryEngine.generateChatPrompt().chatPrompt:', chatPrompt)

        return chatPrompt

    def generateResponse(self, prompt, maxNewTokens=256):
        '''input: prompt.
        output: LLM generated text.'''

        self.model.eval()

        tokenizedInput = self.tokenizer(
            prompt, add_special_tokens=False, return_tensors='pt'
        ).to(self.model.device)

        print('local_LLM.py.QueryEngine.generateResponse().tokenizedInput:', tokenizedInput)

        inputIds = tokenizedInput["input_ids"]
        attentionMask = tokenizedInput["attention_mask"] 

        modelOutput = self.model.generate(
            input_ids=inputIds
            , attention_mask=attentionMask
            , eos_token_id=self.tokenizer.eos_token_id
            , max_new_tokens=maxNewTokens
        )

        decodedOutput = self.tokenizer.batch_decode(
            modelOutput
            , skip_special_tokens=True
        )

        return decodedOutput
    
qe = QueryEngine()

modelId = 'microsoft/Phi-4-mini-instruct'
qe.loadModel(modelId, True)

from time import time

startTime = time()

chatPrompt = qe.generateChatPrompt('안녕하세요?')

response = qe.generateResponse(chatPrompt)
print('local_LLM.py.response:', response)

endTime = time()
print('eplapsedTime:', endTime - startTime)
