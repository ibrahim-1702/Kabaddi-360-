$sourceDir = "C:\Users\msibr\Documents\MCA\SEM_4\Project\kabaddi_trainer\samples\3D\Techniques"
$destDir = "C:\Users\msibr\Documents\MCA\SEM_4\Project\kabaddi_trainer\kabaddi_app\assets\models"

if (!(Test-Path $destDir)) {
    New-Item -ItemType Directory -Force -Path $destDir
}

Copy-Item "$sourceDir\Bonus\USE\Bonus_P2.glb" -Destination "$destDir\Bonus_P2.glb" -Force
Copy-Item "$sourceDir\HandTouch\USE\HandTouch_P2.glb" -Destination "$destDir\HandTouch_P2.glb" -Force

Write-Host "Done copying files."
