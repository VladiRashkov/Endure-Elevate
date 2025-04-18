
# Endure & Elevate
## Important Notice
This application is currently awaiting approval from Strava for an athlete quota increase, which means only one person can use it at this time. Additionally, users must have an active Strava account and be logged into it to utilize the app's features.
## Overview
This project is a dynamic web application that integrates with the Strava API to fetch, analyze, and visualize user activity data. Built with Flask and SQLAlchemy, it provides users with tools to track their workouts, analyze metrics, and view interactive visualizations of their performance.
## Key Features
- User Management: Secure registration, login, and session handling.
- Strava Integration: Authorization and data fetching through Strava's API.
- Activity Analytics: Calculation of VO2 Max, pace dynamics, elevation profiles, and heart rate trends.
- Visualizations: Interactive charts and maps powered by Matplotlib, Folium, and Polyline.
- Modular Architecture: Organized using Flask Blueprints for scalability and maintainability.
- Database Interaction: Efficient data storage and querying with SQLAlchemy ORM.

## Technologies Used
- Backend: Python (Flask, SQLAlchemy)
- Frontend: HTML, CSS (using Flask templates)
- Visualization: Matplotlib, Folium, Polyline
- Database Interaction with SQLAlchemy: Leveraging SQLAlchemy ORM for efficient, scalable, and Pythonic database management. It simplifies the process of creating, querying, and updating database tables, making the app robust and flexible.
- API Integration: Strava

## Setup Instructions
1. Clone the repository.
2. Install dependencies using.
3. Configure environment variables (e.g.,  and Strava credentials).
4. Run the Flask app and access it on http://127.0.0.1:5000.