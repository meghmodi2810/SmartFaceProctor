import subprocess

with open("data.json", "w", encoding="utf-8") as f:
    subprocess.run(
        ["python", "manage.py", "dumpdata", "--natural-primary", "--natural-foreign", "--indent", "4"],
        stdout=f,
        text=True
    )
