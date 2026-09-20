import os
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from typing import Dict, Any

Base = declarative_base()

class Student(Base):
    __tablename__ = 'students'
    id = Column(Integer, primary_key=True)
    student_id = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    attempts = relationship("Attempt", back_populates="student")

class Attempt(Base):
    __tablename__ = 'attempts'
    id = Column(Integer, primary_key=True)
    attempt_id = Column(String, unique=True, nullable=False)
    student_id = Column(String, ForeignKey('students.student_id'), nullable=False)
    topic = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    score = Column(Float, nullable=True)
    total_questions = Column(Integer, nullable=True)
    
    student = relationship("Student", back_populates="attempts")
    question_results = relationship("QuestionResult", back_populates="attempt")

class QuestionResult(Base):
    __tablename__ = 'question_results'
    id = Column(Integer, primary_key=True)
    attempt_id = Column(String, ForeignKey('attempts.attempt_id'), nullable=False)
    question_id = Column(String, nullable=True)
    sub_concept = Column(String, nullable=False)
    question = Column(Text, nullable=False)
    student_answer = Column(Text, nullable=False)
    correct_answer = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    attempt = relationship("Attempt", back_populates="question_results")

class SubconceptMastery(Base):
    __tablename__ = 'subconcept_mastery'
    id = Column(Integer, primary_key=True)
    student_id = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    sub_concept = Column(String, nullable=False)
    attempts = Column(Integer, default=0)
    correct = Column(Integer, default=0)
    accuracy = Column(Float, default=0.0)
    status = Column(String, default="unknown")  # unknown, weak, developing, strong
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class Misconception(Base):
    __tablename__ = 'misconceptions'
    id = Column(Integer, primary_key=True)
    student_id = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    sub_concept = Column(String, nullable=False)
    misconception = Column(Text, nullable=False)
    evidence = Column(Text, nullable=False)
    detected_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.datetime.utcnow)
    active = Column(Boolean, default=True)

class Intervention(Base):
    __tablename__ = 'interventions'
    id = Column(Integer, primary_key=True)
    student_id = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    sub_concept = Column(String, nullable=False)
    misconception = Column(Text, nullable=True)
    strategy = Column(String, nullable=False)
    intervention_text = Column(Text, nullable=False)
    cycle_number = Column(Integer, default=1)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class Verification(Base):
    __tablename__ = 'verifications'
    id = Column(Integer, primary_key=True)
    student_id = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    sub_concept = Column(String, nullable=False)
    cycle_number = Column(Integer, default=1)
    score = Column(Float, nullable=False)
    passed = Column(Boolean, nullable=False)
    evidence = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class LearningEvent(Base):
    __tablename__ = 'learning_events'
    id = Column(Integer, primary_key=True)
    student_id = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    sub_concept = Column(String, nullable=True)
    source_type = Column(String, default="freeform")  # freeform or uploaded_document
    document_name = Column(String, nullable=True)
    mode = Column(String, default="learn")            # learn, revise, test
    status = Column(String, default="EXPOSED")         # EXPOSED, LEARNING, NEEDS_REVISION, MASTERED
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)



class LearnerMemory:
    def __init__(self, db_path="backend/data/edunexus.db"):
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def create_student(self, student_id: str):
        with self.Session() as session:
            student = session.query(Student).filter_by(student_id=student_id).first()
            if not student:
                student = Student(student_id=student_id)
                session.add(student)
                session.commit()
            return student

    def get_student(self, student_id: str):
        with self.Session() as session:
            return session.query(Student).filter_by(student_id=student_id).first()

    def create_attempt(self, attempt_id: str, student_id: str, topic: str):
        with self.Session() as session:
            attempt = session.query(Attempt).filter_by(attempt_id=attempt_id).first()
            if not attempt:
                attempt = Attempt(attempt_id=attempt_id, student_id=student_id, topic=topic)
                session.add(attempt)
                session.commit()
            return attempt

    def save_question_result(
        self, attempt_id: str, sub_concept: str, question: str, 
        student_answer: str, correct_answer: str, is_correct: bool, question_id: str = None
    ):
        with self.Session() as session:
            result = QuestionResult(
                attempt_id=attempt_id,
                sub_concept=sub_concept,
                question=question,
                student_answer=student_answer,
                correct_answer=correct_answer,
                is_correct=is_correct,
                question_id=question_id
            )
            session.add(result)
            session.commit()
            return result

    def complete_attempt(self, attempt_id: str):
        with self.Session() as session:
            attempt = session.query(Attempt).filter_by(attempt_id=attempt_id).first()
            if attempt:
                results = session.query(QuestionResult).filter_by(attempt_id=attempt_id).all()
                total = len(results)
                if total > 0:
                    correct = sum(1 for r in results if r.is_correct)
                    attempt.score = correct / total
                    attempt.total_questions = total
                else:
                    attempt.score = 0.0
                    attempt.total_questions = 0
                session.commit()
                return attempt
            return None

    def _determine_status(self, accuracy: float) -> str:
        if accuracy < 0.60:
            return "weak"
        elif accuracy < 0.80:
            return "developing"
        else:
            return "strong"

    def update_subconcept_performance(self, student_id: str, topic: str, sub_concept: str, is_correct: bool):
        with self.Session() as session:
            mastery = session.query(SubconceptMastery).filter_by(
                student_id=student_id, topic=topic, sub_concept=sub_concept
            ).first()
            
            if not mastery:
                mastery = SubconceptMastery(
                    student_id=student_id, 
                    topic=topic, 
                    sub_concept=sub_concept,
                    attempts=0,
                    correct=0
                )
                session.add(mastery)
                
            mastery.attempts += 1
            if is_correct:
                mastery.correct += 1
                
            mastery.accuracy = float(mastery.correct) / float(mastery.attempts)
            mastery.status = self._determine_status(mastery.accuracy)
            
            session.commit()

    def get_topic_performance(self, student_id: str, topic: str) -> Dict[str, Any]:
        with self.Session() as session:
            masteries = session.query(SubconceptMastery).filter_by(
                student_id=student_id, topic=topic
            ).all()
            
            result = {}
            for m in masteries:
                result[m.sub_concept] = {
                    "attempts": m.attempts,
                    "correct": m.correct,
                    "accuracy": m.accuracy,
                    "status": m.status
                }
            return result

    def get_learner_context(self, student_id: str, topic: str) -> str:
        context_lines = [f"Previous learner performance for {topic}:\n"]
        
        # Sub-concept performance
        perf = self.get_topic_performance(student_id, topic)
        if perf:
            context_lines.append("Sub-concept performance:")
            for sc, data in perf.items():
                acc_percent = int(data['accuracy'] * 100)
                context_lines.append(f"- {sc}: {data['attempts']} attempts, {acc_percent}% accuracy, {data['status']}")
            context_lines.append("")
        else:
            return "No previous learner history available."
            
        with self.Session() as session:
            # Misconceptions
            misconceptions = session.query(Misconception).filter_by(
                student_id=student_id, topic=topic, active=True
            ).all()
            if misconceptions:
                context_lines.append("Known misconceptions:")
                for m in misconceptions:
                    context_lines.append(f"- {m.sub_concept}: {m.misconception}\n  Evidence: {m.evidence}")
                context_lines.append("")
                
            # Interventions
            interventions = session.query(Intervention).filter_by(
                student_id=student_id, topic=topic
            ).all()
            if interventions:
                context_lines.append("Previous interventions:")
                for i in interventions:
                    context_lines.append(f"- {i.sub_concept}: {i.strategy}\n  Cycle: {i.cycle_number}")
                context_lines.append("")
                
            # Verifications
            verifications = session.query(Verification).filter_by(
                student_id=student_id, topic=topic
            ).all()
            if verifications:
                context_lines.append("Previous verification:")
                for v in verifications:
                    status = "Passed" if v.passed else "Failed"
                    context_lines.append(f"- {v.sub_concept}: {status} verification.\n  Score: {v.score}")
                context_lines.append("")

        return "\n".join(context_lines).strip()

    def save_learning_event(
        self, student_id: str, topic: str, sub_concept: str = None, 
        source_type: str = "freeform", document_name: str = None, 
        mode: str = "learn", status: str = "EXPOSED", details: str = None
    ) -> Dict[str, Any]:
        with self.Session() as session:
            event = LearningEvent(
                student_id=student_id,
                topic=topic,
                sub_concept=sub_concept,
                source_type=source_type,
                document_name=document_name,
                mode=mode,
                status=status,
                details=details
            )
            session.add(event)
            session.commit()
            return {
                "id": event.id,
                "student_id": event.student_id,
                "topic": event.topic,
                "sub_concept": event.sub_concept,
                "status": event.status,
                "timestamp": str(event.timestamp)
            }

    def get_topics_for_revision(self, student_id: str) -> list:
        with self.Session() as session:
            # Query learned events
            events = session.query(LearningEvent).filter_by(student_id=student_id).all()
            attempts = session.query(Attempt).filter_by(student_id=student_id).all()
            misconceptions = session.query(Misconception).filter_by(student_id=student_id, active=True).all()
            masteries = session.query(SubconceptMastery).filter_by(student_id=student_id).all()

            topics_dict = {}

            # Populate from learning events
            for e in events:
                if e.topic not in topics_dict:
                    topics_dict[e.topic] = {
                        "topic": e.topic,
                        "source_type": e.source_type,
                        "document_name": e.document_name,
                        "last_studied": str(e.timestamp),
                        "status": e.status,
                        "weak_subconcepts": [],
                        "misconceptions": [],
                        "mastered_subconcepts": []
                    }

            # Populate from attempts
            for a in attempts:
                if a.topic not in topics_dict:
                    topics_dict[a.topic] = {
                        "topic": a.topic,
                        "source_type": "freeform",
                        "document_name": None,
                        "last_studied": str(a.timestamp),
                        "status": "NEEDS_REVISION",
                        "weak_subconcepts": [],
                        "misconceptions": [],
                        "mastered_subconcepts": []
                    }

            # Add misconceptions
            for m in misconceptions:
                if m.topic in topics_dict:
                    topics_dict[m.topic]["misconceptions"].append({
                        "sub_concept": m.sub_concept,
                        "misconception": m.misconception,
                        "evidence": m.evidence
                    })
                    topics_dict[m.topic]["status"] = "NEEDS_REVISION"

            # Add mastery details
            for sm in masteries:
                if sm.topic in topics_dict:
                    if sm.status in ["weak", "developing"]:
                        if sm.sub_concept not in topics_dict[sm.topic]["weak_subconcepts"]:
                            topics_dict[sm.topic]["weak_subconcepts"].append(sm.sub_concept)
                            topics_dict[sm.topic]["status"] = "NEEDS_REVISION"
                    elif sm.status == "strong":
                        if sm.sub_concept not in topics_dict[sm.topic]["mastered_subconcepts"]:
                            topics_dict[sm.topic]["mastered_subconcepts"].append(sm.sub_concept)

            return list(topics_dict.values())

    def delete_topic_data(self, student_id: str, topic: str):
        """Deletes all learning records, events, mastery, and misconceptions for a given student and topic."""
        with self.Session() as session:
            session.query(LearningEvent).filter_by(student_id=student_id, topic=topic).delete()
            session.query(Misconception).filter_by(student_id=student_id, topic=topic).delete()
            session.query(SubconceptMastery).filter_by(student_id=student_id, topic=topic).delete()
            session.query(Verification).filter_by(student_id=student_id, topic=topic).delete()
            session.query(Intervention).filter_by(student_id=student_id, topic=topic).delete()
            attempts = session.query(Attempt).filter_by(student_id=student_id, topic=topic).all()
            for att in attempts:
                session.query(QuestionResult).filter_by(attempt_id=att.attempt_id).delete()
                session.delete(att)
            session.commit()

    def get_quiz_history(self, student_id: str, topic: str):
        with self.Session() as session:
            attempts = session.query(Attempt).filter_by(student_id=student_id, topic=topic).all()
            results = []
            for att in attempts:
                q_results = session.query(QuestionResult).filter_by(attempt_id=att.attempt_id).all()
                for qr in q_results:
                    results.append({
                        "sub_concept": qr.sub_concept,
                        "question": qr.question,
                        "student_answer": qr.student_answer,
                        "correct_answer": qr.correct_answer,
                        "is_correct": qr.is_correct
                    })
            return results

    def get_topic_misconceptions(self, student_id: str, topic: str):
        with self.Session() as session:
            return [
                {"sub_concept": m.sub_concept, "misconception": m.misconception, "evidence": m.evidence}
                for m in session.query(Misconception).filter_by(student_id=student_id, topic=topic, active=True).all()
            ]

    def get_topic_masteries(self, student_id: str, topic: str):
        with self.Session() as session:
            return [
                {"sub_concept": sm.sub_concept, "accuracy": sm.accuracy, "status": sm.status}
                for sm in session.query(SubconceptMastery).filter_by(student_id=student_id, topic=topic).all()
            ]

    def get_learner_summary(self, student_id: str) -> Dict[str, Any]:
        with self.Session() as session:
            student = session.query(Student).filter_by(student_id=student_id).first()
            if not student:
                self.create_student(student_id)

            masteries = session.query(SubconceptMastery).filter_by(student_id=student_id).all()
            misconceptions = session.query(Misconception).filter_by(student_id=student_id, active=True).all()
            events = session.query(LearningEvent).filter_by(student_id=student_id).all()
            attempts = session.query(Attempt).filter_by(student_id=student_id).all()

            mastered_count = len([m for m in masteries if m.status == "strong"])
            weak_count = len([m for m in masteries if m.status in ["weak", "developing"]])
            topics_studied = list(set([e.topic for e in events] + [a.topic for a in attempts]))

            return {
                "student_id": student_id,
                "topics_count": len(topics_studied),
                "topics": topics_studied,
                "mastered_subconcepts_count": mastered_count,
                "weak_subconcepts_count": weak_count,
                "active_misconceptions_count": len(misconceptions),
                "misconceptions": [
                    {
                        "topic": m.topic,
                        "sub_concept": m.sub_concept,
                        "misconception": m.misconception
                    }
                    for m in misconceptions
                ]
            }

    def update_subconcept_mastery(self, student_id: str, topic: str, sub_concept: str, is_correct: bool):
        return self.update_subconcept_performance(student_id, topic, sub_concept, is_correct)

    def save_misconception(self, student_id: str, topic: str, sub_concept: str, misconception: str, evidence: str):
        with self.Session() as session:
            m = session.query(Misconception).filter_by(
                student_id=student_id, topic=topic, sub_concept=sub_concept, active=True
            ).first()
            if not m:
                m = Misconception(
                    student_id=student_id,
                    topic=topic,
                    sub_concept=sub_concept,
                    misconception=misconception,
                    evidence=evidence,
                    active=True
                )
                session.add(m)
            else:
                m.misconception = misconception
                m.evidence = evidence
                m.last_seen = datetime.datetime.utcnow()
            session.commit()
            return m

    def resolve_misconception(self, student_id: str, topic: str, sub_concept: str):
        with self.Session() as session:
            misconceptions = session.query(Misconception).filter_by(
                student_id=student_id, topic=topic, sub_concept=sub_concept, active=True
            ).all()
            for m in misconceptions:
                m.active = False
            session.commit()

    get_learner_profile = get_learner_summary



