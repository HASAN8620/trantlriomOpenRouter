name: OpenRouter Translation Runner

on:
  workflow_dispatch:
  schedule:
    # Har 6 ghante baad automatically chalega aur bacha hua kaam Resume karega
    - cron: '0 */6 * * *'

permissions:
  contents: write

jobs:
  translate:
    runs-on: ubuntu-latest
    timeout-minutes: 350 # 6 ghante se thora pehle safe exit

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install Dependencies
        run: pip install requests

      - name: Run Translation Script
        env:
          OPENROUTER_API_KEYS: ${{ secrets.OPENROUTER_API_KEYS }}
        run: python translate.py

      # 🚀 Timeout ya Error aane par progress repo par commit ho jayegi
      - name: Commit and Push Checkpoint
        if: always()
        run: |
          git config --global user.name 'github-actions[bot]'
          git config --global user.email 'github-actions[bot]@users.noreply.github.com'
          git add american_roman.oxt translation_checkpoint.json || true
          git commit -m "Auto-checkpoint: Saved translation progress for Resume" || echo "No changes to commit"
          git push || echo "Push skipped or failed"
