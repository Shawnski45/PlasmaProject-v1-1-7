import os

root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

for dirpath, dirnames, filenames in os.walk(root):
    for filename in filenames:
        if filename.endswith('.py'):
            fpath = os.path.join(dirpath, filename)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    f.read()
            except UnicodeDecodeError as e:
                print(f'Non-UTF-8 file: {fpath}\n  Error: {e}')
            except Exception as e:
                print(f'Other error in file: {fpath}\n  Error: {e}')
