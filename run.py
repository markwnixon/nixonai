#from webapp import app
from webapp import create_app
app = create_app()
if __name__ == '__main__':
    app.run()
