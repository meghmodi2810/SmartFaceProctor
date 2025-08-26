from django.core.management.base import BaseCommand
from core.models import Exam, Question, User
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Add sample questions to an exam'

    def add_arguments(self, parser):
        parser.add_argument('exam_id', type=int, help='Exam ID to add questions to')

    def handle(self, *args, **options):
        exam_id = options['exam_id']
        
        try:
            exam = Exam.objects.get(id=exam_id)
        except Exam.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Exam with ID {exam_id} does not exist'))
            return

        # Sample questions
        sample_questions = [
            {
                'text': 'What is the output of print(2 ** 3)?',
                'option_a': '5',
                'option_b': '6',
                'option_c': '8',
                'option_d': '9',
                'answer': 'C'
            },
            {
                'text': 'Which SQL statement is used to extract data from a database?',
                'option_a': 'GET',
                'option_b': 'SELECT',
                'option_c': 'EXTRACT',
                'option_d': 'OPEN',
                'answer': 'B'
            },
            {
                'text': 'What does CSS stand for?',
                'option_a': 'Computer Style Sheets',
                'option_b': 'Creative Style System',
                'option_c': 'Cascading Style Sheets',
                'option_d': 'Colorful Style Sheets',
                'answer': 'C'
            },
            {
                'text': 'Which HTML tag is used to define an internal style sheet?',
                'option_a': '<script>',
                'option_b': '<style>',
                'option_c': '<css>',
                'option_d': '<link>',
                'answer': 'B'
            },
            {
                'text': 'Which function is used to read input from the user in Python?',
                'option_a': 'input()',
                'option_b': 'read()',
                'option_c': 'scan()',
                'option_d': 'get()',
                'answer': 'A'
            },
            {
                'text': 'Which is the largest planet in our solar system?',
                'option_a': 'Earth',
                'option_b': 'Mars',
                'option_c': 'Jupiter',
                'option_d': 'Saturn',
                'answer': 'C'
            },
            {
                'text': 'What is the capital of France?',
                'option_a': 'Berlin',
                'option_b': 'London',
                'option_c': 'Paris',
                'option_d': 'Madrid',
                'answer': 'C'
            },
            {
                'text': 'Which element has the chemical symbol "O"?',
                'option_a': 'Gold',
                'option_b': 'Oxygen',
                'option_c': 'Osmium',
                'option_d': 'Iron',
                'answer': 'B'
            },
            {
                'text': 'Who wrote "Romeo and Juliet"?',
                'option_a': 'Charles Dickens',
                'option_b': 'William Shakespeare',
                'option_c': 'Jane Austen',
                'option_d': 'Mark Twain',
                'answer': 'B'
            },
            {
                'text': 'What is the boiling point of water?',
                'option_a': '50°C',
                'option_b': '100°C',
                'option_c': '150°C',
                'option_d': '200°C',
                'answer': 'B'
            }
        ]

        # Delete existing questions for this exam
        Question.objects.filter(exam=exam).delete()

        # Add new questions
        for i, q_data in enumerate(sample_questions):
            question = Question.objects.create(
                exam=exam,
                text=q_data['text'],
                option_a=q_data['option_a'],
                option_b=q_data['option_b'],
                option_c=q_data['option_c'],
                option_d=q_data['option_d'],
                answer=q_data['answer']
            )
            self.stdout.write(f'Added question {i+1}: {q_data["text"][:50]}...')

        self.stdout.write(self.style.SUCCESS(f'Successfully added {len(sample_questions)} questions to exam "{exam.title}"')) 