from Question_generation.models import session, InterviewQA
from datetime import datetime

def format_timestamp(timestamp):
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")

def display_all_interviews():
    # Get all QA pairs ordered by timestamp
    all_qas = session.query(InterviewQA).order_by(InterviewQA.timestamp).all()
    
    if not all_qas:
        print("No interviews found in the database.")
        return
    
    current_date = None
    for qa in all_qas:
        # Format the date for grouping interviews by day
        interview_date = qa.timestamp.date()
        
        # Print date header if it's a new day
        if interview_date != current_date:
            print(f"\n=== Interview Session: {interview_date} ===")
            current_date = interview_date
            
        print(f"\nTime: {format_timestamp(qa.timestamp)}")
        print(f"Difficulty: {qa.difficulty}")
        print(f"Q: {qa.question}")
        print(f"A: {qa.answer if qa.answer else '[No answer yet]'}")
        if qa.score is not None:
            print(f"Score: {qa.score}/10")
        if qa.feedback:
            print(f"Feedback: {qa.feedback}")
        
        # Handle confidence score and feedback safely
        if hasattr(qa, 'confidence_score') and qa.confidence_score is not None:
            print(f"Confidence Score: {qa.confidence_score}/10")
        if hasattr(qa, 'confidence_feedback') and qa.confidence_feedback:
            print(f"Speech Feedback: {qa.confidence_feedback}")
        print("-" * 50)

if __name__ == "__main__":
    print("Retrieving interview data from database...")
    display_all_interviews()
