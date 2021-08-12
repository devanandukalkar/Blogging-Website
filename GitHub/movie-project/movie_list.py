from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField
from wtforms.validators import DataRequired, NumberRange
import requests
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('APP_SECRET_KEY')
Bootstrap(app)

# Database configuration
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Heroku PostgreSQL connection
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///movie_collection.db')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://", "postgresql://", 1)

db = SQLAlchemy(app)

# API to pull movies
MOVIE_API_ENDPOINT = "https://api.themoviedb.org/3/search/movie"
MOVIE_API_KEY = os.environ.get('API_KEY')


# Create SQLite Movie Database
class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), unique=True, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(1000), nullable=False)
    rating = db.Column(db.Float, nullable=False)
    ranking = db.Column(db.Integer)
    review = db.Column(db.String(1000), nullable=False)
    img_url = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"{self.id} - {self.title} - {self.rating}"


# db.create_all()


# Form to edit movie rating
class EditMovieForm(FlaskForm):
    rating = FloatField(label="Your Rating Out Of 10 e.g. 7.5", validators=[NumberRange(min=0, max=10)])
    review = StringField(label="Your Review", validators=[DataRequired()])
    submit = SubmitField(label="Done")


# Form to add a movie
class AddMovieForm(FlaskForm):
    movie_title = StringField(label="Movie Title", validators=[DataRequired()])
    add_button = SubmitField(label="Add Movie")


# Home Page
@app.route("/")
def home():
    # Extract list of movies sorted by rating
    all_movies = Movie.query.order_by(Movie.rating).all()

    # Loop through each movie and assign lowest rating from top to bottom
    for i in range(len(all_movies)):
        all_movies[i].ranking = len(all_movies) - i
    db.session.commit()
    return render_template("index.html", movies=all_movies)


# Edit movie rating
@app.route("/edit", methods=["GET", "POST"])
def edit_movie_rating():
    rating_form = EditMovieForm()
    movie_id = request.args.get('id')  # Getting ID from URL http://127.0.0.1:5000/edit?id=1
    movie_record = Movie.query.get(movie_id)  # Query database to retrieve the records
    if rating_form.validate_on_submit():
        # update the records
        movie_record.rating = float(rating_form.rating.data)
        movie_record.review = rating_form.review.data
        db.session.commit()
        return redirect(url_for('home'))  # redirect to home page
    return render_template("edit.html", form=rating_form)


# Delete movie
@app.route("/delete")
def delete_movie():
    movie_id = request.args.get('id')  # Getting ID from URL http://127.0.0.1:5000/edit?id=1
    movie_to_delete = Movie.query.get(movie_id)
    db.session.delete(movie_to_delete)
    db.session.commit()
    return redirect(url_for('home'))


# Add Movie
@app.route("/add", methods=["GET", "POST"])
def add_movie():
    add_movie_form = AddMovieForm()
    if add_movie_form.validate_on_submit():
        movies_response = requests.get(MOVIE_API_ENDPOINT, params={
            "api_key": MOVIE_API_KEY,
            "query": add_movie_form.movie_title.data,
            "page": 1
        })
        select_movies = [{
                "movie_id": movie["id"],
                "movie_title": movie["title"],
                "movie_release_date": movie["release_date"]
            } for movie in (movies_response.json()["results"])]
        # print(select_movies)
        return render_template("select.html", select_movies=select_movies)
    return render_template("add.html", add_form=add_movie_form)


# Find Movie using an API
@app.route("/find")
def find_movie():
    # print("Adding new movie")
    movie_api_id = request.args.get('id')
    movie_details_api = f"https://api.themoviedb.org/3/movie/{movie_api_id}"
    movie_details = requests.get(movie_details_api, params={"api_key": MOVIE_API_KEY}).json()
    new_movie = Movie(title=movie_details["title"],
                      year=movie_details["release_date"].split("-")[0],
                      description=movie_details["overview"],
                      rating=movie_details["vote_average"],
                      review=movie_details["tagline"],
                      img_url=f'https://image.tmdb.org/t/p/w500/{movie_details["poster_path"]}'
                      )
    db.session.add(new_movie)
    db.session.commit()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
