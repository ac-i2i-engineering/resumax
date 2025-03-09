# ResuMax Backend Documentation

## Overview

The ResuMax backend is a Django-based application that provides the API and core logic for the ResuMax application. It handles user authentication, conversation management, and interaction with the AI model for resume analysis and generation.

## Key Components

*   **Django:** The web framework used to build the backend.
*   **Django REST Framework:**  Used for building the API endpoints.
*   **Google Gemini API:**  The AI model used for resume analysis and content generation.
*   **Database:**  (Specify the database used, e.g., PostgreSQL, SQLite) Stores user data, conversation history, and other application data.

## Setup and Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd resumax_backend
    ```

2.  **Create a virtual environment:**

    ```bash
    python -m venv env
    source env/bin/activate  # On Linux/macOS
    env\Scripts\activate  # On Windows
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure the application:**

    *   **`secret.py`:**  This file is crucial for storing sensitive information such as the `GEMINI_API_KEY` and the Django `SECRET_KEY`.  **Do not commit this file to version control.**  Create a [secret.py](http://_vscodecontentref_/2) file in the [resumax_backend](http://_vscodecontentref_/3) directory with the following structure:

        ```python
        # filepath:resumax/resumax_backend/resumax_backend/secret.py
        SECRET_KEY = 'your_django_secret_key'
        GEMINI_API_KEY = 'your_gemini_api_key'
        ```

    *   **`resumax_backend/settings.py`:**  Update the [settings.py](http://_vscodecontentref_/4) file to import the [secret.py](http://_vscodecontentref_/5) settings:

        ```python
        # filepath:resumax/resumax_backend/resumax_backend/settings.py
        from .secret import SECRET_KEY, GEMINI_API_KEY

        # ... other settings ...

        SECRET_KEY = SECRET_KEY
        GEMINI_API_KEY = GEMINI_API_KEY
        ```

5.  **Run migrations:**

    ```bash
    python manage.py migrate
    ```

6.  **Create a superuser:**

    ```bash
    python manage.py createsuperuser
    ```

7.  **Start the development server:**

    ```bash
    python manage.py runserver
    ```

## API Endpoints ([resumax_api](http://_vscodecontentref_/6))

The [resumax_api](http://_vscodecontentref_/7) app provides the following endpoints:

*   **`GET /api/threads`:**
    *   **Description:** Retrieves all conversation threads for the authenticated user.
    *   **Authentication:** Requires user authentication (login).
    *   **Response:**
        ```json
        [
            {
                "id": "thread_id",
                "title": "Thread Title",
                "created_at": "2025-03-09T00:00:00Z",
                "updated_at": "2025-03-09T00:00:00Z"
            },
            ...
        ]
        ```
*   **`GET /api/thread/<thread_id>`:**
    *   **Description:** Retrieves all conversations within a specific thread.
    *   **Authentication:** Requires user authentication (login).
    *   **Parameters:**
        *   [thread_id](http://_vscodecontentref_/8): The ID of the conversation thread.
    *   **Response:**
        ```json
        {
            "conversations": [
                {
                    "prompt": "User prompt",
                    "response": "AI response"
                },
                ...
            ]
        }
        ```
*   **`POST /api/thread/<thread_id>`:**
    *   **Description:** Creates a new conversation message within a specific thread.  Handles both text prompts and file uploads.
    *   **Authentication:** Requires user authentication (login).
    *   **Parameters:**
        *   [thread_id](http://_vscodecontentref_/9): The ID of the conversation thread.
        *   [prompt-text](http://_vscodecontentref_/10): (Optional) The text prompt from the user.
        *   [prompt-file](http://_vscodecontentref_/11): (Optional) A file uploaded by the user (e.g., a resume in PDF format).
    *   **Request (form-data):**

        ```form-data
        prompt-text: "Please review my resume."
        prompt-file: (file - resume.pdf)
        ```

    *   **Response:**

        ```json
        {
            "text": "AI generated response"
        }
        ```

## Models ([resumax_algo](http://_vscodecontentref_/12))

*   **[ConversationsThread](http://_vscodecontentref_/13):** Represents a conversation thread.
    *   [title](http://_vscodecontentref_/14):  The title of the conversation thread.
    *   [user](http://_vscodecontentref_/15):  The user who owns the conversation thread (ForeignKey to `User`).
    *   [created_at](http://_vscodecontentref_/16):  The date and time the thread was created.
    *   [updated_at](http://_vscodecontentref_/17):  The date and time the thread was last updated.
*   **[Conversation](http://_vscodecontentref_/18):** Represents a single turn in a conversation.
    *   [prompt](http://_vscodecontentref_/19): The user's prompt.
    *   [response](http://_vscodecontentref_/20): The AI's response.
    *   [thread](http://_vscodecontentref_/21): The conversation thread this message belongs to (ForeignKey to [ConversationsThread](http://_vscodecontentref_/22)).
*   **[AttachedFile](http://_vscodecontentref_/23):** Represents a file attached to a conversation.
    *   [Conversation](http://_vscodecontentref_/24): The conversation this file is attached to (ForeignKey to [Conversation](http://_vscodecontentref_/25)).
    *   `fileName`: The name of the attached file.

## Important Notes

*   **`secret.py`:**  As mentioned above, the [secret.py](http://_vscodecontentref_/26) file is critical for storing sensitive information.  Ensure it is properly configured and **never committed to version control.**  Add it to your [.gitignore](http://_vscodecontentref_/27) file.
*   **Error Handling:** The API endpoints include basic error handling, but you should implement more robust error handling and logging in a production environment.
*   **Security:**  Review and implement appropriate security measures, such as input validation, rate limiting, and protection against common web vulnerabilities.
*   **Asynchronous Tasks:** For long-running tasks (e.g., complex resume analysis), consider using asynchronous task queues (e.g., Celery) to improve performance and responsiveness.

## Contributing

(Add contribution guidelines here)

## License

(Add license information here)