from django.core.management.base import BaseCommand
from api.models import Tutorial

class Command(BaseCommand):
    help = 'Create initial tutorial data'
    
    def handle(self, *args, **options):
        tutorials = [
            {
                'name': 'hand_touch',
                'description': 'Hand touch kabaddi movement',
                'expert_pose_path': 'expert_poses/hand_touch.npy'
            },
            {
                'name': 'toe_touch', 
                'description': 'Toe touch kabaddi movement',
                'expert_pose_path': 'expert_poses/toe_touch.npy'
            },
            {
                'name': 'bonus',
                'description': 'Bonus kabaddi movement',
                'expert_pose_path': 'expert_poses/bonus.npy'
            }
        ]
        
        for tutorial_data in tutorials:
            tutorial, created = Tutorial.objects.get_or_create(
                name=tutorial_data['name'],
                defaults={
                    'description': tutorial_data['description'],
                    'expert_pose_path': tutorial_data['expert_pose_path']
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created tutorial: {tutorial.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Tutorial already exists: {tutorial.name}')
                )