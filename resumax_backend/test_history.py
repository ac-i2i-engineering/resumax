#!/usr/bin/env python3
"""
Test script to verify conversation history functionality
"""
import os
import django
import asyncio

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'resumax_backend.settings')
django.setup()

from resumax_algo.models import ConversationsThread, Conversation
from resumax_algo.gemini_model import generate_response
from django.contrib.auth.models import User

async def test_conversation_history():
    print("🧪 Testing Conversation History\n")
    
    # Get or create a test user
    user, created = User.objects.get_or_create(username='test_user', defaults={
        'email': 'test@example.com',
        'first_name': 'Test',
        'last_name': 'User'
    })
    
    # Create a test thread
    thread, created = ConversationsThread.objects.get_or_create(
        title="Test Conversation",
        user=user
    )
    thread_id = thread.id
    print(f"📋 Using thread ID: {thread_id}")
    
    # Clear any existing conversations for clean test
    Conversation.objects.filter(thread=thread).delete()
    print("🧹 Cleared existing conversations\n")
    
    # Test 1: First message (no history)
    print("1️⃣ Testing first message (should show no history):")
    response1 = await generate_response(
        "Hi, my name is John and I'm a software engineer", 
        thread_id=thread_id
    )
    
    # Save first conversation manually to database
    Conversation.objects.create(
        thread=thread,
        prompt="Hi, my name is John and I'm a software engineer",
        response=response1
    )
    print(f"✅ Response 1: {response1[:100]}...\n")
    
    # Test 2: Second message (should load history)
    print("2️⃣ Testing second message (should show 2 history messages):")
    response2 = await generate_response(
        "What should I include in my resume?", 
        thread_id=thread_id
    )
    
    # Save second conversation
    Conversation.objects.create(
        thread=thread,
        prompt="What should I include in my resume?",
        response=response2
    )
    print(f"✅ Response 2: {response2[:100]}...\n")
    
    # Test 3: Third message (should load all history)
    print("3️⃣ Testing third message (should show 4 history messages):")
    response3 = await generate_response(
        "Remember my name and profession from earlier?", 
        thread_id=thread_id
    )
    print(f"✅ Response 3: {response3[:100]}...\n")
    
    # Test 4: New conversation (no thread_id)
    print("4️⃣ Testing new conversation (no thread_id, should show no history):")
    response4 = await generate_response("Hello, I'm a new user")
    print(f"✅ Response 4: {response4[:100]}...\n")
    
    print("🎉 Test completed! Check the debug output above to see history loading.")

if __name__ == "__main__":
    asyncio.run(test_conversation_history())