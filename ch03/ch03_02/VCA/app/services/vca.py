##########################################
# Vibe Code Assistant (Class Version)
##########################################

# pip install wheel
# pip install google-adk google-generativeai
# pip install rich

import os
import asyncio

import google.generativeai as genai
# from getpass import getpass
from google.adk.agents import Agent, LoopAgent, SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part
from google.adk.tools import google_search, ToolContext
from google.adk.tools.google_search_tool import GoogleSearchTool
from requests import Session


class CodingAssistant:

    def __exit_loop(self, tool_context: ToolContext) -> dict:
        """Call this function ONLY when the program code is approved, signaling the loop should end.

        Returns:
            A dictionary containing final program with key final_program.
        """
        print(f'[Tool Call] exit_loop triggered by {tool_context.agent_name}')
        tool_context.actions.escalate = True    # 도구는 tool_context.actions.escalate = True를 설정하여 성공을 알린다.

        current_program = tool_context.state.get("current_program", 'No current_program found.')
        print('exit_loop().current_program: ', current_program)

        print(f'[Tool Call] Final code: {current_program}')
        return {"final_program": current_program}

    def __init__(self, apiKey):
        self.apiKey = apiKey
        # genai 모듈은 Google Generative AI API와의 연결을 설정하는 역할을 하며, Google ADK Agent가 Gemini 모델을 사용할 수 있도록 API 키를 구성한다.
        # genai 모듈은 직접 호출되지 않고, Google ADK의 Agent가 내부적으로 사용한다.
        # 현재 genai 모듈은 싱글톤 패턴으로 동작하는 전역 설정 모듈이다.
        # 애플리케이션에서 하나의 API 키만 사용하고 여러 CodingAssistant 인스턴스가 같은 API 키를 사용할 수 있도록 한다.
        genai.configure(api_key=self.apiKey)
        os.environ['GOOGLE_API_KEY'] = self.apiKey

        # Agent definition
        self.architectAgent = Agent(
            name='architect_agent'
            , model='gemini-2.5-flash'
            , description='An agent which analyzes user request and drawing program requirements from the user request.'
            , instruction='''
            You are an expert software architect.
            You are given a user's request for a software program. You need to analyze the request and draw a program requirements.
            Then, you need to design a software architecture and describe a software design document.
            '''
            , tools=[google_search]
            , output_key='sw_design_document'
        )

        self.coderAgent = Agent(
            name='coder_agent'
            , model='gemini-2.5-flash'
            , description='An agent which can be used to write a program code based on a software design document.'
            , instruction=f'''
            Your are an expert software developer.
            Your mission is writing a program code draft which satisfies the software design document, {{sw_design_document}}.
            '''
            , tools = [google_search]
            , output_key='current_program'
        )

        self.LINTING_COMPLETION_PHRASE = 'The program code is clear, brief and has no syntax error.'

        self.refinerAgent = Agent(
            name='refiner_agent'
            , model='gemini-2.5-flash'
            , description='An agent which refines a program code to be clear, brief and having no syntax error.'
            , instruction=f"""
            You are an expert software developer.
            Your mission is refining a program based on criticism.
            Original Request: {{sw_design_document}}
            Critique: {{criticism}}
            You can use GoogleSearchTool to search for information such as programming language syntax which is necessary for rewriting the program.
            If the critique is '{self.LINTING_COMPLETION_PHRASE}', you MUST first output and save the current program code, then call the 'exit_loop' tool.
            Else, generate a NEW program code that addresses the critique. Output only the new program code.
            """
            , tools=[GoogleSearchTool(bypass_multi_tools_limit=True), self.__exit_loop]
            , output_key='current_program'
        )
        
        self.FUNCTION_RESPONSE_KEY = 'final_program'

        self.linterAgent = Agent(
            name='linter_agent'
            , model='gemini-2.5-flash'
            , description='An agent which can be used to review a program code based on the software design document and language syntax.'
            , instruction=f'''
            You are an expert on programming development and programming language.
            Software design document: {{sw_design_document}}
            Current program code: {{current_program}}
            Your mission is to review the current program code whether or not it is clear and brief.
            Please also check syntax of the program code during reviewing process.
            If the target program code has been written clear, brief and having no error, you MUST respond with {self.LINTING_COMPLETION_PHRASE}.
            '''
            , tools = [google_search]
            , output_key='criticism'
        )

        self.iterativeCoderAgent = LoopAgent(
            name='iterative_coder_agent'
            , sub_agents=[self.linterAgent, self.refinerAgent]
            , max_iterations=3
        )

        self.supervisorAgent = SequentialAgent(
            name='coding_assistant_supervisor_agent'
            , sub_agents=[self.architectAgent, self.coderAgent, self.iterativeCoderAgent]
            , description="A workflow that iteratively designs and refines a software program to meet the user's request."
        )

    async def __runAgentQuery(
        self
        , agent: Agent
        , query: str
        , userId: str
        , sessionService: InMemorySessionService
        , session: Session
        , isRouter: bool = False
    ):
        """Initializes a runner and executes a query for a given agent and session."""
        print(f'Running query for agent: {agent.name} with query: {query}')

        # 1. Create a runner instance
        runner = Runner(
            agent=agent
            , session_service=sessionService
            , app_name=agent.name
        )

        finalResponse = ''
        finalResponseFrom = ''
        finalResponses = {}
        functionResponses = {}

        try:
            # 2. Run the agent
            runResult = runner.run_async(
                user_id=userId
                , session_id=session.id
                , new_message=Content(parts=[Part(text=query)], role='user')
            )

            # 3. Process the run results
            try:
                async for event in runResult:
                    isFinalResponse = event.is_final_response()
                    functionResps = event.get_function_responses()

                    # if event.is_final_response():
                    if isFinalResponse:
                        print(f'[Final Response Event]: {event.content}, author: {event.author}')

                        try:
                            for part in event.content.parts:
                                finalResponses[event.author] = part.text
                        except Exception as e:
                                print('event.content.parts[part].text is not found:', e)
                    else:
                        if not isRouter:
                            # show the intermediate steps of the agent
                            print(f'Event.content: {event.content}, author: {event.author}')
                        else:
                            pass

                    # if event.get_function_responses():
                    if functionResps:
                        print(f'[Function Responses]: {functionResps}, author: {event.author}')
                        functionResponses[event.author] = functionResps[0].response.get(self.FUNCTION_RESPONSE_KEY)
                    else:
                        pass

                if finalResponses.get('refiner_agent'):
                    finalResponse = finalResponses.get('refiner_agent')
                    finalResponseFrom = 'refiner_agent'
                elif finalResponses.get('coder_agent'):
                    finalResponse = finalResponses.get('coder_agent')
                    finalResponseFrom = 'coder_agent'
                else:
                    pass    # empty string, no result yet.

                if functionResponses.get('refiner_agent'):
                    finalResponse = functionResponses.get('refiner_agent')
                    finalResponseFrom = 'refiner_agent(function response)'
                else:
                    pass    # keep previous finalResponse
            except asyncio.CancelledError:
                print('__runAgentQuery().runResult iteration cancelled.')
                raise  # CancelledError는 다시 발생시켜 상위로 전파
        except asyncio.CancelledError:
            # CancelledError는 다시 발생시켜 상위로 전파
            raise
        except Exception as e:
            finalResponse = f'Error during running agent: {e}'

        # 4. Print the final response
        if not isRouter:
            print('\n' + '='*50)
            print(f'Final Response(by {finalResponseFrom}):')
            print(finalResponse)
            print('='*50 + '\n')
        else:
            # pass
            print('\n' + '-'*50)
            print('Router Response(Class Version):')
            print(finalResponse)
            print('-'*50 + '\n')

        # 5. Return the final response to the caller
        return finalResponse

    async def runCodingAssistant(
        self
        , userId: str
        , query: str
    ):
        """Runs the coding assistant.
        Args: user id, query
        Returns: final response
        """
        runAgentQueryTask = None

        # 1. Initialize a session service
        sessionService = InMemorySessionService()

        # 2. Create a session for the coding assistant
        workerSession = await sessionService.create_session(
            app_name=self.supervisorAgent.name
            , user_id=userId
        )

        # 3. Run the coding assistant
        runAgentQueryTask = asyncio.create_task(self.__runAgentQuery(self.supervisorAgent, query, userId, sessionService, workerSession))

        try:
            fr = await runAgentQueryTask
        except asyncio.CancelledError:
            print('runCodingAssistant().runAgentQueryTask cancelled.')
            # 내부 태스크가 아직 실행 중이면 취소
            if runAgentQueryTask and not runAgentQueryTask.done():
                runAgentQueryTask.cancel()
                try:
                    await runAgentQueryTask
                except asyncio.CancelledError:
                    pass
            raise  # CancelledError를 다시 발생시켜 상위로 전파
        finally:
            # 리소스 정리
            runAgentQueryTask = None

        return fr   # final response
