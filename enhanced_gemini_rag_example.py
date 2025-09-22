# Enhanced Gemini Implementation for Resume Review with RAG-like capabilities
from google import genai
from google.genai import types
import pathlib
import asyncio

class GeminiResumeAnalyzer:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
    
    async def analyze_resume_with_context(self, resume_files, user_query, conversation_history=None):
        """
        Enhanced resume analysis with conversation context and structured output
        This replaces traditional RAG with Gemini's native capabilities
        """
        
        # Build context from conversation history
        context_prompt = self._build_context_prompt(conversation_history)
        
        # Enhanced system prompt for better responses
        system_prompt = """
        You are an expert resume reviewer and career advisor. Analyze the provided resume(s) 
        and provide detailed, actionable feedback. Consider:
        
        1. Visual layout and formatting
        2. Content structure and organization  
        3. Skills presentation and relevance
        4. Experience descriptions and impact
        5. Education and certifications
        6. Overall professional presentation
        
        Provide responses in this structured format:
        
        ## Executive Summary
        [Brief overall assessment]
        
        ## Strengths
        [Key positive aspects]
        
        ## Areas for Improvement  
        [Specific recommendations]
        
        ## Next Steps
        [Actionable items]
        
        ## Specific Answer
        [Direct response to user's question]
        """
        
        # Process multiple resume files if provided
        file_parts = []
        if resume_files:
            for file_path in resume_files:
                file_content = await self._read_file_async(file_path)
                file_parts.append(
                    types.Part.from_bytes(data=file_content, mime_type='application/pdf')
                )
        
        # Combine all content
        full_prompt = f"{system_prompt}\n\n{context_prompt}\n\nUser Question: {user_query}"
        content_parts = file_parts + [full_prompt]
        
        # Generate response with structured output
        response = self.client.models.generate_content(
            model="gemini-1.5-flash",
            contents=content_parts,
            generation_config={
                "temperature": 0.3,  # More consistent responses
                "top_p": 0.8,
                "max_output_tokens": 2048,
            }
        )
        
        return response.text
    
    def _build_context_prompt(self, conversation_history):
        """Build context from previous conversations"""
        if not conversation_history:
            return ""
        
        context = "Previous conversation context:\n"
        for conv in conversation_history[-3:]:  # Last 3 conversations for context
            context += f"User: {conv.prompt}\nAssistant: {conv.response[:200]}...\n\n"
        
        return context
    
    async def _read_file_async(self, filepath):
        """Async file reading"""
        return await asyncio.to_thread(pathlib.Path(filepath).read_bytes)
    
    async def batch_analyze_resumes(self, resume_files, analysis_type="comprehensive"):
        """
        Analyze multiple resumes for comparison or batch processing
        Gemini can handle up to 1000 pages in a single request
        """
        analysis_prompts = {
            "comprehensive": "Provide comprehensive analysis of each resume",
            "comparison": "Compare these resumes and rank them for hiring",
            "skills_gap": "Identify skills gaps across all resumes",
        }
        
        prompt = analysis_prompts.get(analysis_type, analysis_prompts["comprehensive"])
        return await self.analyze_resume_with_context(resume_files, prompt)

# Usage example (this replaces your current retriever.py functionality)
async def generate_enhanced_response(query, file_urls=None, conversation_history=None):
    """
    Enhanced response generation that replaces both HuggingFace RAG and basic Gemini
    """
    analyzer = GeminiResumeAnalyzer(api_key=settings.GEMINI_API_KEY)
    
    # Convert file URLs to file paths
    file_paths = []
    if file_urls:
        file_paths = [pathlib.Path(str(settings.BASE_DIR) + url) for url in file_urls]
    
    # Generate response with context and structured output
    response = await analyzer.analyze_resume_with_context(
        resume_files=file_paths,
        user_query=query,
        conversation_history=conversation_history
    )
    
    return response
