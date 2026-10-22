import sqlite3

conn = sqlite3.connect("college_faq.db")
cursor = conn.cursor()

print("=== Add New College FAQ ===")

keywords = input(
    "Enter keywords separated by spaces: "
).strip().lower()

answer = input(
    "Enter the answer: "
).strip()

if keywords and answer:
    cursor.execute(
        "INSERT INTO faqs (keywords, answer) VALUES (?, ?)",
        (keywords, answer)
    )

    conn.commit()
    print("FAQ added successfully! 🎉")
else:
    print("Keywords and answer cannot be empty.")

conn.close()