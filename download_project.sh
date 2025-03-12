
#!/bin/bash
echo "Creating zip file of your CryptoScalp AI project..."
zip -r cryptoscalp_project.zip ./ -x "*.git*" -x "*.replit*" -x "__pycache__*" -x "*.nix*"
echo "Done! File created: cryptoscalp_project.zip"
echo "You can download this file from the Files panel in Replit."
