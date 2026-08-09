from database import Base, SessionLocal, engine
from models import Note, User
from ranking_dataset import RANKING_DATASET
from ai_sample_notes import AI_SAMPLE_NOTES

SEED_USERS = [
    {"id": 1, "name": "Alice", "email": "alice@example.com", "password": "alicepass123"},
    {"id": 2, "name": "Bob", "email": "bob@example.com", "password": "bobpass123"},
]

SEED_NOTES = [
    {"id": 1, "owner_id": 1, "title": "Standup Summary", "tag": "work", "content": "Discussed sprint progress, blockers on the payments API integration, and the plan for the demo on Friday."},
    {"id": 2, "owner_id": 1, "title": "Sprint Retro Notes", "tag": "work", "content": "Retro highlighted communication gaps between frontend and backend teams and agreed on daily syncs going forward."},
    {"id": 3, "owner_id": 2, "title": "One on One", "tag": "work", "content": "Quick check-in, no blockers, discussed career growth goals for next quarter."},
    {"id": 4, "owner_id": 1, "title": "Morning Run", "tag": "health", "content": "Ran 5km along the river trail before breakfast, felt great."},
    {"id": 5, "owner_id": 2, "title": "Doctor Visit", "tag": "health", "content": "Annual checkup went well, blood pressure normal, scheduled next visit in six months."},
    {"id": 6, "owner_id": 1, "title": "Pasta Recipe", "tag": "recipes", "content": "Boil pasta, saute garlic in olive oil, add tomatoes, basil, and a pinch of chili flakes."},
    {"id": 7, "owner_id": 2, "title": "Smoothie Recipe", "tag": "recipes", "content": "Blend banana, spinach, almond milk, and a spoon of peanut butter for breakfast."},
    {"id": 8, "owner_id": 1, "title": "Flight Booking", "tag": "travel", "content": "Booked a round trip flight for the December vacation, window seat confirmed."},
    {"id": 9, "owner_id": 2, "title": "Random Thought", "tag": "random", "content": "Maybe the library needs a better recommendation system based on reading history."},
    {"id": 10, "owner_id": 1, "title": "Quote To Remember", "tag": "random", "content": "Done is better than perfect, keep shipping."},
]

def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            for data in SEED_USERS:
                db.add(User(**data))
            db.commit()

        if db.query(Note).count() == 0:
            for data in SEED_NOTES:
                data = data.copy()
                data.pop("id", None)
                db.add(Note(**data))
            for data in RANKING_DATASET:
                db.add(Note(
                    title=data["title"], content=data["content"],
                    tag="kb-demo", owner_id=1
                ))
            for data in AI_SAMPLE_NOTES:
                db.add(Note(
                    title=data["title"], content=data["content"],
                    tag="ai-demo", owner_id=2
                ))
            db.commit()
        print("Database seeded successfully.")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
