@echo off
echo ======================================================================
echo Re-encoding Review1 Videos for Browser Compatibility
echo ======================================================================
echo.
echo This will re-encode all 12 videos with H.264 codec (browser-compatible)
echo Original files will be backed up with .original extension
echo.
pause

cd /d "%~dp0"

echo.
echo Level-1 Videos (5 files)...
echo ======================================================================

cd review1\level1_pose\outputs

for %%f in (*.mp4) do (
    if not "%%f"=="%%~nf_web.mp4" (
        echo Processing: %%f
        ren "%%f" "%%f.original"
        ffmpeg -i "%%f.original" -c:v libx264 -preset fast -crf 23 -c:a aac -y "%%f"
        if errorlevel 1 (
            echo ERROR: Failed to encode %%f
            ren "%%f.original" "%%f"
        ) else (
            echo ✓ %%f re-encoded successfully
            del "%%f.original"
        )
    )
)

cd ..\..\..

echo.
echo Level-2 Videos (4 files)...
echo ======================================================================

cd review1\level2\Outputs

for %%f in (*.mp4) do (
    echo Processing: %%f
    ren "%%f" "%%f.original"
    ffmpeg -i "%%f.original" -c:v libx264 -preset fast -crf 23 -c:a aac -y "%%f"
    if errorlevel 1 (
        echo ERROR: Failed to encode %%f
        ren "%%f.original" "%%f"
    ) else (
        echo ✓ %%f re-encoded successfully
        del "%%f.original"
    )
)

cd ..\..\..

echo.
echo Level-3 Videos (1 file)...
echo ======================================================================

cd review1\visualization\level3

for %%f in (*.mp4) do (
    echo Processing: %%f
    ren "%%f" "%%f.original"
    ffmpeg -i "%%f.original" -c:v libx264 -preset fast -crf 23 -c:a aac -y "%%f"
    if errorlevel 1 (
        echo ERROR: Failed to encode %%f
        ren "%%f.original" "%%f"
    ) else (
        echo ✓ %%f re-encoded successfully
        del "%%f.original"
    )
)

cd ..\..\..

echo.
echo Level-4 Videos (1 file)...
echo ======================================================================

cd review1\visualization\level4

for %%f in (*.mp4) do (
    echo Processing: %%f
    ren "%%f" "%%f.original"
    ffmpeg -i "%%f.original" -c:v libx264 -preset fast -crf 23 -c:a aac -y "%%f"
    if errorlevel 1 (
        echo ERROR: Failed to encode %%f
        ren "%%f.original" "%%f"
    ) else (
        echo ✓ %%f re-encoded successfully
        del "%%f.original"
    )
)

cd ..\..\..

echo.
echo ======================================================================
echo All videos re-encoded successfully!
echo ======================================================================
echo.
echo You can now refresh the Gallery page and all videos should play.
echo.
pause
