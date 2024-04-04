from django.shortcuts import render
from openai import OpenAI
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.http import StreamingHttpResponse
from dotenv import load_dotenv
from uuid import uuid4
from .models import *
import json
import re
import PyPDF2
import os
load_dotenv()



# Handle topic selection API requests
class TopicAPIView(APIView):
    def post(self, request):
        data = request.data.get('topic', [])
        if not data:
            return Response({'error': 'No message provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            request.session["topic"] = data
            return Response({"msg": "success"}, status=status.HTTP_200_OK)
        except Exception as e:
            # Log the error for debugging purposes
            print("Error in processing:", e)
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Extract text from PDF files
def read_pdf(pdf_path):
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        num_pages = len(reader.pages)
        text = ''
        for page_num in range(num_pages):
            page = reader.pages[page_num]
            text += page.extract_text()
        text = text.replace('\n', ' ')
        return text


# Extract information from text
def extract_information(text):
    # Initialize variables to store extracted information
    education = ""
    work_experience = ""
    technology = ""
    skills = []

    # Split the text into sections based on "\n\n"
    sections = text.split("\n\n")

    # Iterate over each section
    for section in sections:
        # Extract educational information
        if "Educational Information:" in section:
            education = extract_section_content(section)
        # Extract work experience information
        elif "Work Experience Information:" in section:
            work_experience = extract_section_content(section)
        # Extract skills and technology
        elif "Skills and Technology:" in section:
            lines = section.split('\n')
            for line in lines:
                if "- Hard Skills:" in line:
                    technology = extract_section_content(line)
                elif "- Scripting:" in line or "- Source Code Management Tools:" in line or "- Languages:" in line:
                    skills.append(extract_skills(line))

    return {
        "education": education,
        "work_experience": work_experience,
        "technology": technology,
        "skills": skills
    }

# Extract content from a section
def extract_section_content(section):
    # Split the section into lines
    lines = section.split("\n")
    # Remove the section header
    lines = [line for line in lines if ":" not in line]
    # Join the lines to form the section content
    content = "\n".join(lines)
    return content.strip()

# Extract skills from a line
def extract_skills(line):
    # Split the line into skills
    skills_line = line.split(":")[1].strip()
    # Split the skills using commas
    skills_list = skills_line.split(",")
    # Strip each skill and return
    return [skill.strip() for skill in skills_list]



def update_and_insert_pdf_data(data):
    collection = get_doc_collection()
    session_id = data.get("session_id")
    existing_doc = collection.find_one({"session_id": session_id})
    if existing_doc:
        # Update existing document
        collection.update_one({"session_id": session_id}, {"$set": data})
    else:
        # Insert new document
        collection.insert_one(data)

# Handle PDF file upload and extraction of information
class UploadPdfAPIView(APIView):
    def post(self, request):
        try:
            # Assuming 'file' is the name of the file field in the request
            uploaded_file = request.data.get('file')
            if not uploaded_file:
                return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
            # Ensure the media directory exists
            media_dir = settings.MEDIA_ROOT
            if not os.path.exists(media_dir):
                os.makedirs(media_dir)
            # Save the file to the media directory
            file_path = os.path.join(media_dir, uploaded_file.name)
            with open(file_path, 'wb') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            # Process PDF and get text
            pdf_text = read_pdf(file_path)
            prompt = {
                "role": "system",
                "content": """!IMPORTANT Please follow these steps:
                        1. Your sole purpose is to understand the text and extract the following information: educational information, work experience information, skills and technology. 
                        2. If you successfully extract this information, respond with Message: 'Success' and provide the data containing all the extracted information.
                        """
            }

            user_message_object = {
                "role": "user",
                "content": pdf_text
            }
            client = OpenAI(api_key=os.environ.get('OPEN_AI_KEY'))
            # Call OpenAI API to generate completion based on prompts
            response=client.chat.completions.create(
                model="gpt-4",
                messages=[prompt, user_message_object],
                max_tokens=2048,
                temperature=0
            )

            result = response.choices[0].message.content
            result_text = extract_information(result)
            data = {
                "session_id": request.session._session_key,
                "pdf_data": result_text
            }
            update_and_insert_pdf_data(data)
            request.session["topic"] = result_text
            return Response({"msg": "success"}, status=status.HTTP_200_OK)
        except Exception as e:
            # Log the error for debugging purposes
            print("Error in processing:", e)
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Update or insert conversation data
def update_or_insert_conversation(request, topic, conversation):
    data = {
        "session_id": request.session._session_key,
        "topic": topic,
        "conversation": [conversation]
    }
    new_data = None
    conversation = [conversation]
    # Check if session_id already exists in the collection
    existing_data = get_collection().find_one({"session_id": data["session_id"], 'topic':topic})

    # If session_id exists, update the existing document
    if existing_data:
        total_conversation = None
        get_conversation = existing_data.get('conversation')
        if isinstance(get_conversation, list) and isinstance(conversation, list):
            total_conversation = get_conversation + conversation
            new_data = {
                    "session_id": request.session._session_key,
                    "topic": topic,
                    "conversation": total_conversation
                }

        if isinstance(get_conversation, dict) and isinstance(conversation, dict):
            new_list = []
            new_list.append(get_conversation)
            new_list.append(conversation)
            total_conversation = new_list
        new_values = {"$set": {"topic": topic, "conversation": total_conversation}}
        get_collection().update_one({"session_id": data["session_id"]}, new_values)
        print("Updated existing document")
    else:
        # If session_id does not exist, insert a new document
        get_collection().insert_one(data)
        if "_id" in data:
            data["_id"] = str(data["_id"])
        print("Inserted new document")
        new_data = data

    # Save data to conversation.txt
    with open(f"{request.session._session_key}.txt", "w") as file:
        json.dump(new_data, file)

# Handle user questions and generate responses
conversation = []
class QuestionAPIView(APIView):
    def post(self, request):
        try:
            topic = request.session.get("topic")
            if not topic:
                return Response({'error': 'No topic provided'}, status=status.HTTP_400_BAD_REQUEST)

            question = request.data.get('q', '')
            if not question:
                return Response({'error': 'No message provided'}, status=status.HTTP_400_BAD_REQUEST)

            # Initialize or get the 'data' list from the session
            data = request.session.get('data', [])
            request.session.modified = True

            # OpenAI API integration
            client = OpenAI(api_key=os.environ.get('OPEN_AI_KEY'))

            # Set up prompts for GPT-4
            prompts = {
                "role": "system",
                "content": f"""!IMPORTANT Please follow these steps:
                                1. You are a chatbot that will help users with {topic}.
                                2. Query: {question}
                                3. The query should be related to the topic only.Otherwise send the response that "Question is not related to the topic"
                            """
            }

            user_message_object = {
                "role": "user",
                "content": question
            }

            # Generate a unique key for the conversation entry
            conversation_key = str(uuid4())

            # Initialize conversation entry
            conversation_entry = {
                "q": question,
                "resp": ""  # Initialize an empty string for response
            }

            # Add previous questions to prompts
            for conv in data:
                prev_question = conv.get('q')
                if prev_question:
                    prompts['content'] += f"\nPrevious question: {prev_question}"

            def generate_response():
                global concatenated_response  # Declare concatenated_response as global
                concatenated_response = ""  # Initialize concatenated_response

                messages = [prompts, user_message_object]
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=messages,
                    temperature=0.5,
                    stream=True
                )
                for chunk in response:
                    try:
                        chunk_message = chunk.choices[0].delta.content
                        if chunk_message is not None:
                            concatenated_response += ' '.join(chunk_message.split()) + " "
                        yield chunk_message
                    except Exception as e:
                        print("Error processing response:", e)

                conversation_entry["resp"] = concatenated_response.strip()
                conversation.append(conversation_entry)
                update_or_insert_conversation(request, topic, conversation_entry)

            # Return streaming response
            return StreamingHttpResponse(generate_response(), content_type='text/event-stream')
        except Exception as e:
            # Log the error for debugging purposes
            print("Error in processing:", e)
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SessionClearAPIView(APIView):
    def delete(self, request):
        try:
            # Check if the file exists
            file_path = f"{request.session._session_key}.txt"
            if os.path.exists(file_path):
                # Remove the file
                os.remove(file_path)
            # Clear the session
            request.session.clear()
            return Response({"msg": "success"}, status=status.HTTP_200_OK)
        except Exception as e:
            # Log the error for debugging purposes
            print("Error in processing:", e)
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)