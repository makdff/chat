from db import init_db, create_chat, get_chats, add_message, get_chat_messages, delete_chat

def test_sqlite_flow():
    print("Initializing Database...")
    init_db()
    
    print("\nCreating a test chat session...")
    chat_id = create_chat("Test Chat Session")
    print(f"Created chat with ID: {chat_id}")
    
    print("\nAdding test messages...")
    add_message(chat_id, "user", "Hello, this is a test prompt.")
    add_message(chat_id, "assistant", "Hello! This is a test response.", "test-model", "Test Provider")
    
    print("\nRetrieving chat sessions...")
    chats = get_chats()
    for c in chats:
        print(f"Chat ID: {c['id']}, Title: {c['title']}, Created At: {c['created_at']}")
        
    print("\nRetrieving messages...")
    messages = get_chat_messages(chat_id)
    for m in messages:
        print(f"Role: {m['role']}, Content: {m['content']}, Model: {m.get('model_name')}, Provider: {m.get('provider')}")
        
    print(f"\nDeleting chat session {chat_id}...")
    delete_chat(chat_id)
    
    remaining_chats = get_chats()
    print(f"Remaining chats count: {len(remaining_chats)}")
    print("\nAll database tests passed successfully!")

if __name__ == "__main__":
    test_sqlite_flow()
