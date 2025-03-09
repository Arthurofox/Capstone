import os
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
import asyncio

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts.chat import SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize ChatOpenAI
llm = ChatOpenAI(
    model="gpt-4o-mini", 
    temperature=0.7,
    api_key=os.getenv("OPENAI_API_KEY")
)

class CareerAssistantPromptHandler:
    """
    Handles prompt construction and management for the career assistant
    """
    
    def __init__(self, prompt_xml_path: str):
        """
        Initialize the prompt handler with XML prompt file
        
        Args:
            prompt_xml_path: Path to the XML prompt file
        """
        self.prompt_xml_path = prompt_xml_path
        self.prompt_content = self._load_xml_prompt()
        
    def _load_xml_prompt(self) -> Dict[str, Any]:
        """
        Load and parse the XML prompt file
        
        Returns:
            Dictionary containing parsed XML content
        """
        try:
            tree = ET.parse(self.prompt_xml_path)
            root = tree.getroot()
            
            # Parse the XML into a structured dictionary
            prompt_dict = self._parse_xml_element(root)
            return prompt_dict
        except Exception as e:
            print(f"Error loading XML prompt: {str(e)}")
            return {}
    
    def _parse_xml_element(self, element) -> Any:
        """
        Recursively parse XML element into Python data structure
        
        Args:
            element: XML element to parse
            
        Returns:
            Parsed data structure (dict, list, or string)
        """
        if len(element) == 0:
            return element.text.strip() if element.text else ""
        
        result = {}
        for child in element:
            child_tag = child.tag
            child_result = self._parse_xml_element(child)
            
            if child_tag in result:
                if not isinstance(result[child_tag], list):
                    result[child_tag] = [result[child_tag]]
                result[child_tag].append(child_result)
            else:
                result[child_tag] = child_result
                
        return result
    
    def create_system_prompt(self) -> str:
        """
        Create system prompt from XML content
        
        Returns:
            Formatted system prompt string
        """
        if not self.prompt_content:
            return "You are a helpful career assistant named Sophia."
        
        # Extract key sections for the system prompt
        identity = self.prompt_content.get('Identity', {})
        name = identity.get('n', 'Sophia')
        role = identity.get('Role', 'Career Guidance Professional')
        personality = identity.get('Personality', {})
        traits = personality.get('Traits', '')
        
        # Construct the system prompt
        system_prompt = f"""You are {name}, a {role} with the following personality traits: {traits}.

            CAREER ASSISTANT GUIDELINES:
            1. Your purpose is to help students with career planning, job searching, resume review, and interview preparation.
            2. You should be warm, professional, and empathetic in your responses.
            3. Provide practical, actionable advice tailored to the student's situation.
            4. Ask probing questions to understand their needs, goals, and concerns.
            5. When appropriate, suggest interview practice without being asked.
            6. Connect career choices to deeper values and aspirations.
            7. Stay aware of modern workplace trends and emerging industries.
            8. Respect boundaries and redirect inappropriate requests.
            9. You cannot access real-time job listings or guarantee employment outcomes.
            10. You cannot provide specialized legal or mental health support.

            Be proactive in guiding the conversation, but responsive to the student's needs.
            """
        
        return system_prompt
    
    def create_langchain_prompt(self) -> ChatPromptTemplate:
        """
        Create LangChain prompt template for chat interface
        
        Returns:
            LangChain ChatPromptTemplate
        """
        system_template = self.create_system_prompt()
        system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)
        
        human_template = "{input}"
        human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)
        
        chat_prompt = ChatPromptTemplate.from_messages([
            system_message_prompt,
            human_message_prompt
        ])
        
        return chat_prompt
    
    async def generate_response(self, user_input: str, chat_history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Generate a response from the career assistant
        
        Args:
            user_input: User's message
            chat_history: Optional chat history
            
        Returns:
            Assistant's response
        """
        try:
            # Prepare LangChain message format
            messages = [SystemMessage(content=self.create_system_prompt())]
            
            # Add chat history if provided
            if chat_history:
                for message in chat_history:
                    if message["role"] == "user":
                        messages.append(HumanMessage(content=message["content"]))
                    elif message["role"] == "assistant":
                        messages.append(SystemMessage(content=message["content"]))
            
            # Add user's message
            messages.append(HumanMessage(content=user_input))
            
            # Generate response using LangChain ChatOpenAI
            response = await llm.ainvoke(messages)
            
            return response.content
        
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            return f"I apologize, but I encountered an error. Please try again later."