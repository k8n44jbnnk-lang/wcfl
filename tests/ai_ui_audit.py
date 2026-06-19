import asyncio
import os
import sys

# Ensure the required packages are installed before importing
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from browser_use import Agent
    from browser_use.browser.browser import Browser, BrowserConfig
except ImportError:
    print("Required packages are missing. Please run:")
    print("pip install browser-use langchain-google-genai playwright")
    print("playwright install")
    sys.exit(1)

async def run_audit():
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("❌ ERROR: GOOGLE_API_KEY environment variable is not set.")
        print("Please set it in your terminal before running this script:")
        print("  $env:GOOGLE_API_KEY=\"your-gemini-api-key\"")
        sys.exit(1)

    print("Initializing Gemini 2.0 Flash for Visual Audit...")
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    
    # Configure browser to be headless for automated testing
    browser = Browser(config=BrowserConfig(headless=True))

    task_description = (
        "Go to http://127.0.0.1:5000/standings. "
        "Analyze the page visually and verify the following: "
        "1. Is the Fantasy Standings leaderboard visible? "
        "2. Look at the Rank 1 player card. Does it have distinct styling, such as a gold border, badge, or specific colors compared to others? "
        "3. Are the bottom navigation icons/tabs visible? "
        "Report your findings clearly based on what you see."
    )

    print(f"\n🚀 Starting AI Agent with task:\n\"{task_description}\"\n")
    agent = Agent(
        task=task_description,
        llm=llm,
        browser=browser
    )

    result = await agent.run()
    
    print("\n" + "="*50)
    print("📊 AI VISUAL AUDIT RESULTS")
    print("="*50)
    # the result object contains the history. we can print the final result.
    if result.is_done():
        print(result.final_result())
    else:
        print("Agent did not complete successfully.")
        print(result)
        
    await browser.close()

if __name__ == "__main__":
    # Prevent ProactorEventLoop issues on Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(run_audit())
