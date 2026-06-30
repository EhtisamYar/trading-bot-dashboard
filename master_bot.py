import subprocess
import sys
import os

def main():
    while True:
        print("\n" + "=" * 80)
        print("🤖 ULTIMATE TRADING BOT SUITE")
        print("=" * 80)
        print("  📌 Choose your mode:")
        print("")
        print("  1. 🌍 ULTIMATE BOT (Single Coin Deep Dive)")
        print("     → Multi-source price fetch, news sentiment, full technical analysis")
        print("")
        print("  2. ⚡ ELITE SCANNER (Fast Market Scan)")
        print("     → Top 40 coins, parallel fetching, 80%+ confidence signals")
        print("")
        print("  3. ❌ EXIT")
        print("=" * 80)
        
        choice = input("\n👉 Enter your choice (1-3): ").strip()
        
        if choice == '1':
            print("\n🔄 Launching Ultimate Bot...\n")
            try:
                # Check if ultimate_bot.py exists
                if not os.path.exists("ultimate_bot.py"):
                    print("❌ Error: ultimate_bot.py file not found!")
                    print("   Make sure ultimate_bot.py is in the same folder.")
                else:
                    subprocess.run([sys.executable, "ultimate_bot.py"])
            except Exception as e:
                print(f"❌ Error: {e}")
                
        elif choice == '2':
            print("\n🔄 Launching Elite Scanner...\n")
            try:
                # YOUR FILE NAME IS scanner_elite2.py
                if not os.path.exists("scanner_elite2.py"):
                    print("❌ Error: scanner_elite2.py file not found!")
                    print("   Make sure scanner_elite2.py is in the same folder.")
                else:
                    subprocess.run([sys.executable, "scanner_elite2.py"])
            except Exception as e:
                print(f"❌ Error: {e}")
                
        elif choice == '3':
            print("\n👋 Goodbye! Happy Trading!")
            break
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    main()