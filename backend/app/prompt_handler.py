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
    using a complete XML structure.
    """
    
    def __init__(self, prompt_xml_path: str):
        """
        Initialize the prompt handler with an XML prompt file.
        
        Args:
            prompt_xml_path: Path to the XML prompt file.
        """
        self.prompt_xml_path = prompt_xml_path
        self.prompt_content = self._load_xml_prompt()
        
    def _load_xml_prompt(self) -> Dict[str, Any]:
        """
        Load and parse the XML prompt file.
        
        Returns:
            Dictionary containing the parsed XML content.
        """
        try:
            tree = ET.parse(self.prompt_xml_path)
            root = tree.getroot()
            prompt_dict = self._parse_xml_element(root)
            return prompt_dict
        except Exception as e:
            print(f"Error loading XML prompt: {str(e)}")
            return {}
    
    def _parse_xml_element(self, element) -> Any:
        """
        Recursively parse an XML element into a Python data structure.
        
        Args:
            element: XML element to parse.
            
        Returns:
            Parsed data structure (string, dict, or list).
        """
        # Base case: if no children, return text content
        if len(element) == 0:
            return element.text.strip() if element.text else ""
        
        result = {}
        for child in element:
            child_tag = child.tag
            child_result = self._parse_xml_element(child)
            # Handle multiple children with the same tag
            if child_tag in result:
                if not isinstance(result[child_tag], list):
                    result[child_tag] = [result[child_tag]]
                result[child_tag].append(child_result)
            else:
                result[child_tag] = child_result
        return result

    def create_system_prompt(self) -> str:
        """
        Create a system prompt string by incorporating all sections of the XML.
        
        Returns:
            A comprehensive system prompt string.
        """
        if not self.prompt_content:
            return "You are a helpful career assistant named Sophia."
        
        prompt_lines = []
        
        # Identity Section
        identity = self.prompt_content.get('Identity', {})
        name = identity.get('Name', 'Sophia')
        role = identity.get('Role', 'Career Guidance Professional')
        prompt_lines.append("Identity:")
        prompt_lines.append(f"  Name: {name}")
        prompt_lines.append(f"  Role: {role}")
        
        # Background within Identity
        background = identity.get('Background', {})
        if background:
            prompt_lines.append("  Background:")
            for key, value in background.items():
                prompt_lines.append(f"    {key}: {value}")
                
        # Personality within Identity
        personality = identity.get('Personality', {})
        if personality:
            prompt_lines.append("  Personality:")
            for key, value in personality.items():
                prompt_lines.append(f"    {key}: {value}")
        
        # Interaction Guidelines Section
        interaction = self.prompt_content.get('InteractionGuidelines', {})
        if interaction:
            prompt_lines.append("\nInteraction Guidelines:")
            for key, value in interaction.items():
                prompt_lines.append(f"  {key}: {value}")
        
        # Expertise Areas Section
        expertise = self.prompt_content.get('ExpertiseAreas', {})
        if expertise:
            prompt_lines.append("\nExpertise Areas:")
            for area, content in expertise.items():
                prompt_lines.append(f"  {area}:")
                if isinstance(content, dict):
                    for key, value in content.items():
                        if isinstance(value, list):
                            prompt_lines.append(f"    {key}:")
                            for item in value:
                                prompt_lines.append(f"      - {item}")
                        else:
                            prompt_lines.append(f"    {key}: {value}")
                else:
                    prompt_lines.append(f"    {content}")
        
        # Responsible AI Boundaries Section
        boundaries = self.prompt_content.get('ResponsibleAIBoundaries', {})
        if boundaries:
            prompt_lines.append("\nResponsible AI Boundaries:")
            for key, value in boundaries.items():
                prompt_lines.append(f"  {key}: {value}")
        
        # Career Context Awareness Section
        context = self.prompt_content.get('CareerContextAwareness', {})
        if context:
            prompt_lines.append("\nCareer Context Awareness:")
            for key, value in context.items():
                if isinstance(value, list):
                    prompt_lines.append(f"  {key}:")
                    for item in value:
                        prompt_lines.append(f"    - {item}")
                else:
                    prompt_lines.append(f"  {key}: {value}")
        
        # Proactive Advising Section
        advising = self.prompt_content.get('ProactiveAdvising', {})
        if advising:
            prompt_lines.append("\nProactive Advising:")
            for key, value in advising.items():
                prompt_lines.append(f"  {key}: {value}")
        
        # Standard Career Assistant Guidelines
        prompt_lines.append("\nCareer Assistant Guidelines:")
        guidelines = [
            "Your purpose is to help students with career planning, job searching, resume review, and interview preparation.",
            "Be warm, professional, and empathetic.",
            "Provide practical, actionable advice tailored to the student's situation.",
            "Ask probing questions to understand their needs, goals, and concerns.",
            "Suggest interview practice when appropriate.",
            "Connect career choices to deeper values and aspirations.",
            "Stay aware of modern workplace trends and emerging industries.",
            "Respect boundaries and redirect inappropriate requests.",
            "You cannot access real-time job listings or guarantee employment outcomes.",
            "You cannot provide specialized legal or mental health support."
        ]
        for guideline in guidelines:
            prompt_lines.append(f"  - {guideline}")
        
        # Add instruction to avoid using section headers
        prompt_lines.append("\nIMPORTANT: Your responses should be conversational and natural without using explicit section headers like 'Acknowledgment:', 'Insight:', etc.")
        
        return "\n".join(prompt_lines)
    
    async def generate_response(self, user_input: str, chat_history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Generate a response from the career assistant.
        
        Args:
            user_input: The user's input message.
            chat_history: Optional list of previous chat messages.
            
        Returns:
            The assistant's response.
        """
        try:
            # Prepare messages for LangChain
            messages = [SystemMessage(content=self.create_system_prompt())]
            
            if chat_history:
                for message in chat_history:
                    if message["role"] == "user":
                        messages.append(HumanMessage(content=message["content"]))
                    elif message["role"] == "assistant":
                        messages.append(SystemMessage(content=message["content"], name="assistant"))
                    elif message["role"] == "system":
                        # Add additional system messages for context (like resume data)
                        messages.append(SystemMessage(content=message["content"]))
            
            messages.append(HumanMessage(content=user_input))
            
            response = await llm.ainvoke(messages)
            return response.content
        
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            return "I encountered an error. Please try again later."

# For testing purposes, you can run this module directly:
if __name__ == "__main__":
    handler = CareerAssistantPromptHandler(prompt_xml_path="backend/app/prompts/career_assistant_prompt.xml")
    print(handler.create_system_prompt())
