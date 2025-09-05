from agent.conversation_agent import ConversationAgent

def cli():
    agent = ConversationAgent()
    import asyncio
    try:
        asyncio.run(agent.start_conversation())
    except (KeyboardInterrupt, asyncio.CancelledError):
        # Graceful exit on Ctrl+C without showing traceback
        
        exit(0)
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        exit(1)

if __name__ == "__main__":
    cli()