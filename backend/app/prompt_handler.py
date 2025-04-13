"""
Module: prompt_handler.py
-------------------------
This module defines the CareerAssistantPromptHandler class, which is responsible for
loading and processing an XML file containing structured prompts for the career assistant.
It constructs a system prompt that sets the identity, background, guidelines, and other 
contextual information necessary for the assistant to provide informed and personalized responses.
Additionally, it interacts with a language model (ChatOpenAI) to generate responses based on
user input and chat history.

Key Components:
    - Loading and parsing an XML prompt file.
    - Creating a comprehensive system prompt string.
    - Generating responses using the language model with context.
"""

import os
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
import asyncio

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts.chat import SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# Load environment variables (e.g., API keys) from the .env file.
load_dotenv()

# Initialize the language model used for generating chat responses.
llm = ChatOpenAI(
    model="gpt-4o-mini", 
    temperature=0.7,
    api_key=os.getenv("OPENAI_API_KEY")
)

class CareerAssistantPromptHandler:
    """
    Handles prompt construction and message generation for the career assistant.
    
    This class loads an XML prompt file containing structured sections for identity, 
    guidelines, expertise, and more. It then builds a comprehensive system prompt and 
    uses chat history along with the user input to generate responses via the language model.
    """
    
    def __init__(self, prompt_xml_path: str):
        """
        Initialize the prompt handler with the given XML prompt file.
        
        Args:
            prompt_xml_path (str): Path to the XML prompt file.
        """
        self.prompt_xml_path = prompt_xml_path
        self.prompt_content = self._load_xml_prompt()
        
    def _load_xml_prompt(self) -> Dict[str, Any]:
        """
        Load and parse the XML prompt file into a dictionary.
        
        Returns:
            Dict[str, Any]: A dictionary representing the XML structure.
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
        Recursively parse an XML element and convert it into a Python data structure.
        
        Args:
            element: The XML element to parse.
            
        Returns:
            Any: Parsed data as a string, dictionary, or list.
        """
        # Base case: If the element has no children, return its text content.
        if len(element) == 0:
            return element.text.strip() if element.text else ""
        
        result = {}
        # Process each child element recursively.
        for child in element:
            child_tag = child.tag
            child_result = self._parse_xml_element(child)
            # Handle multiple children with the same tag by grouping them in a list.
            if child_tag in result:
                if not isinstance(result[child_tag], list):
                    result[child_tag] = [result[child_tag]]
                result[child_tag].append(child_result)
            else:
                result[child_tag] = child_result
        return result

    def create_system_prompt(self) -> str:
        """
        Construct a comprehensive system prompt string that sets the context for the assistant.
        
        This method uses several sections from the XML prompt file such as Identity, Interaction Guidelines,
        Expertise Areas, and more to build a detailed prompt. If the XML prompt fails to load, it falls back
        to a default prompt.
        
        Returns:
            str: The complete system prompt for initializing the assistant.
        """
        if not self.prompt_content:
            return "You are a helpful career assistant named Sophia."
        
        prompt_lines = []
        
        # Identity Section: Set the assistant's name and role.
        identity = self.prompt_content.get('Identity', {})
        name = identity.get('Name', 'Sophia')
        role = identity.get('Role', 'Career Guidance Professional')
        prompt_lines.append("Identity:")
        prompt_lines.append(f"  Name: {name}")
        prompt_lines.append(f"  Role: {role}")
        
        # Background: Include any background details provided.
        background = identity.get('Background', {})
        if background:
            prompt_lines.append("  Background:")
            for key, value in background.items():
                prompt_lines.append(f"    {key}: {value}")
                
        # Personality: Add personality traits if available.
        personality = identity.get('Personality', {})
        if personality:
            prompt_lines.append("  Personality:")
            for key, value in personality.items():
                prompt_lines.append(f"    {key}: {value}")
        
        # Interaction Guidelines: Define how the assistant should interact.
        interaction = self.prompt_content.get('InteractionGuidelines', {})
        if interaction:
            prompt_lines.append("\nInteraction Guidelines:")
            for key, value in interaction.items():
                prompt_lines.append(f"  {key}: {value}")
        
        # Expertise Areas: Enumerate fields or topics the assistant is knowledgeable about.
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
        
        # Responsible AI Boundaries: Outline any limitations or ethical boundaries.
        boundaries = self.prompt_content.get('ResponsibleAIBoundaries', {})
        if boundaries:
            prompt_lines.append("\nResponsible AI Boundaries:")
            for key, value in boundaries.items():
                prompt_lines.append(f"  {key}: {value}")
        
        # Career Context Awareness: Include specifics about the career context.
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
        
        # Proactive Advising: Provide advice protocols or additional instructions.
        advising = self.prompt_content.get('ProactiveAdvising', {})
        if advising:
            prompt_lines.append("\nProactive Advising:")
            for key, value in advising.items():
                prompt_lines.append(f"  {key}: {value}")
        
        # Standard Career Assistant Guidelines: List general guidelines for assisting students.
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
        
        # Additional instruction to ensure natural conversation without explicit headers.
        prompt_lines.append("\nIMPORTANT: Your responses should be conversational and natural without using explicit section headers like 'Acknowledgment:', 'Insight:', etc.")
        
        return "\n".join(prompt_lines)
    
    async def generate_response(self, user_input: str, chat_history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Generate a response from the career assistant based on user input and prior conversation history.
        
        The method builds a list of messages starting with the comprehensive system prompt,
        followed by the conversation history (if provided), and ending with the current user input.
        It then uses the asynchronous language model invocation to generate and return the assistant's reply.
        
        Args:
            user_input (str): The latest message from the user.
            chat_history (Optional[List[Dict[str, str]]]): Prior messages in the conversation.
        
        Returns:
            str: The generated response from the assistant.
        """
        try:
            # Start with the system prompt to set the context.
            messages = [SystemMessage(content=self.create_system_prompt())]
            
            # Append chat history messages maintaining the role distinctions.
            if chat_history:
                for message in chat_history:
                    if message["role"] == "user":
                        messages.append(HumanMessage(content=message["content"]))
                    elif message["role"] == "assistant":
                        messages.append(SystemMessage(content=message["content"], name="assistant"))
                    elif message["role"] == "system":
                        # Use any additional system messages as part of the context.
                        messages.append(SystemMessage(content=message["content"]))
            
            # Add the current user input to the messages list.
            messages.append(HumanMessage(content=user_input))
            
            # Asynchronously generate a response using the language model with the complete context.
            response = await llm.ainvoke(messages)
            return response.content
            
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            return "I encountered an error. Please try again later."

# For testing purposes, the module can output the generated system prompt.
if __name__ == "__main__":
    handler = CareerAssistantPromptHandler(prompt_xml_path="backend/app/prompts/career_assistant_prompt.xml")
    print(handler.create_system_prompt())
