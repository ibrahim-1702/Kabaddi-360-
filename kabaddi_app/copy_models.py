import shutil
import os

src1 = r"C:\Users\msibr\Documents\MCA\SEM_4\Project\kabaddi_trainer\samples\3D\Techniques\Bonus\USE\Bonus_P2.glb"
src2 = r"C:\Users\msibr\Documents\MCA\SEM_4\Project\kabaddi_trainer\samples\3D\Techniques\HandTouch\USE\HandTouch_P2.glb"
dest_dir = r"C:\Users\msibr\Documents\MCA\SEM_4\Project\kabaddi_trainer\kabaddi_app\assets\models"

os.makedirs(dest_dir, exist_ok=True)
try:
    shutil.copy(src1, os.path.join(dest_dir, "Bonus_P2.glb"))
    print("Copied Bonus")
except Exception as e:
    print("Error copying Bonus:", e)
    
try:
    shutil.copy(src2, os.path.join(dest_dir, "HandTouch_P2.glb"))
    print("Copied HandTouch")
except Exception as e:
    print("Error copying HandTouch:", e)

print("Finished")
