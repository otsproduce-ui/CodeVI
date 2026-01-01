"""
Test Graphistry installation and registration
"""
import graphistry

print(f"Graphistry version: {graphistry.__version__}")

# To register, you need to:
# 1. Sign up at https://hub.graphistry.com
# 2. Get your API credentials from your account
# 3. Replace the placeholders below with your actual credentials

# Example registration (uncomment and fill in your credentials):
# graphistry.register(
#     api=3,
#     protocol="https",
#     server="hub.graphistry.com",
#     personal_key_id="YOUR_KEY_ID_HERE",
#     personal_key_secret="YOUR_KEY_SECRET_HERE"
# )

print("\nTo register Graphistry:")
print("1. Visit https://hub.graphistry.com and sign up")
print("2. Get your API credentials from your account settings")
print("3. Use graphistry.register() with your credentials")
print("\nExample usage:")
print("graphistry.register(api=3, protocol='https', server='hub.graphistry.com',")
print("                  personal_key_id='your_key_id', personal_key_secret='your_key_secret')")

