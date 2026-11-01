from app.database.session import engine, Base
from app.models import User, Project, Conversation, Message, AgentTask, FileChange, ToolExecution

def init_db():
    print("[*] Initializing DevPilot AI database tables...")
    Base.metadata.create_all(bind=engine)
    print("[+] Database tables initialized successfully.")

if __name__ == "__main__":
    init_db()
