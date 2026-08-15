"""
main.py
Thin WSGI entrypoint for Vercel deployment. Deliberately NOT named app.py:
Vercel's @vercel/python builder imports the entrypoint file using its
filename (minus .py) as the module name, so a file named app.py becomes
the module "app" -- which then shadows/collides with the top-level app/
package of the same name and breaks `from app import create_app` with
"ImportError: cannot import name 'create_app' from 'app'". Naming this
file main.py avoids that collision entirely.
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
