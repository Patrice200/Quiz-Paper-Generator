from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3

app = Flask(__name__)
app.secret_key = "super_secret_key"

def get_db_connection():
    try:
        conn = sqlite3.connect('quiz_bank.db')
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None



# Home route (Login page)
@app.route('/')
def login():
    return render_template('login.html')


# Registration page for both students and educators
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        university = request.form['university']
        user_type = request.form['user_type']
        conn = get_db_connection()
        conn.execute('INSERT INTO users (username, password, role,university) VALUES (?, ?, ?,?)', (username, password, user_type, university))
        conn.commit()
        conn.close()
        flash(f"Registered successfully as {user_type}. Please log in.", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

# Student dashboard for viewing and taking quizzes
@app.route('/student_dashboard')
def student_dashboard():
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if user is None:
        flash("User not found. Please log in again.", "danger")
        return redirect(url_for('login'))
    quizzes = conn.execute('SELECT * FROM quizzes').fetchall()  # Fetch all quizzes
    results = conn.execute('SELECT quiz_id, score FROM quiz_results WHERE user_id = ?', (session['user_id'],)).fetchall()  # Fetch quiz results for the user

    # Create a dictionary to store the scores
    quiz_scores = {result['quiz_id']: result['score'] for result in results}

    # Fetch the number of questions for each quiz
    quiz_questions = {quiz['id']: conn.execute('SELECT COUNT(*) FROM questions WHERE quiz_id = ?', (quiz['id'],)).fetchone()[0] for quiz in quizzes}

    conn.close()

    return render_template('student_dashboard.html', user=user, quizzes=quizzes, quiz_scores=quiz_scores, quiz_questions=quiz_questions)

# Educator dashboard for managing quizzes
@app.route('/educator_dashboard')
def educator_dashboard():
    if 'user_id' not in session or session.get('role') != 'educator':
        return redirect(url_for('login'))

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if user is None:
        flash("User not found. Please log in again.", "danger")
        return redirect(url_for('login'))

    quizzes = conn.execute('SELECT * FROM quizzes WHERE created_by = ?', (session['user_id'],)).fetchall()  # Fetch quizzes created by the logged-in educator
    students = conn.execute('SELECT * FROM users WHERE role = ? AND university = ?', ('student', user['university'])).fetchall()  # Fetch students from the same university
    conn.close()

    return render_template('educator_dashboard.html', user=user, quizzes=quizzes, students=students)

# Create a new quiz
@app.route('/create_quiz', methods=['GET', 'POST'])
def create_quiz():
    if 'user_id' not in session or session.get('role') != 'educator':
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        difficulty = request.form['difficulty']
        created_by = session['user_id']
        conn = get_db_connection()
        conn.execute('INSERT INTO quizzes (title, difficulty, created_by) VALUES (?, ?, ?)', (title, difficulty, created_by))
        conn.commit()
        conn.close()
        flash('Quiz created successfully!', 'success')
        return redirect(url_for('educator_dashboard'))

    return render_template('create_quiz.html')

# Edit a quiz
@app.route('/edit_quiz/<int:quiz_id>', methods=['GET', 'POST'])
def edit_quiz(quiz_id):
    if 'user_id' not in session or session.get('role') != 'educator':
        return redirect(url_for('login'))

    conn = get_db_connection()
    quiz = conn.execute('SELECT * FROM quizzes WHERE id = ?', (quiz_id,)).fetchone()

    if request.method == 'POST':
        title = request.form['title']
        difficulty = request.form['difficulty']
        conn.execute('UPDATE quizzes SET title = ?, difficulty = ? WHERE id = ?', (title, difficulty, quiz_id))
        conn.commit()
        conn.close()
        return redirect(url_for('educator_dashboard'))

    conn.close()
    return render_template('edit_quiz.html', quiz=quiz)

# Delete a quiz
@app.route('/delete_quiz/<int:quiz_id>')
def delete_quiz(quiz_id):
    if 'user_id' not in session or session.get('role') != 'educator':
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute('DELETE FROM quizzes WHERE id = ?', (quiz_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('educator_dashboard'))

# Add a question to a quiz
@app.route('/add_question/<int:quiz_id>', methods=['GET', 'POST'])
def add_question(quiz_id):
    if 'user_id' not in session or session.get('role') != 'educator':
        return redirect(url_for('login'))

    if request.method == 'POST':
        question_text = request.form['question_text']
        correct_answer = request.form['correct_answer']
        conn = get_db_connection()
        conn.execute('INSERT INTO questions (quiz_id, question_text, correct_answer) VALUES (?, ?, ?)', (quiz_id, question_text, correct_answer))
        conn.commit()
        conn.close()
        flash('Question and answer added successfully!', 'success')
        return redirect(url_for('educator_dashboard'))

    return render_template('add_question.html', quiz_id=quiz_id)

@app.route('/take_quiz/<int:quiz_id>', methods=['GET', 'POST'])
def take_quiz(quiz_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()

    # Fetch the quiz and its questions
    quiz = conn.execute('SELECT * FROM quizzes WHERE id = ?', (quiz_id,)).fetchone()
    questions = conn.execute('SELECT * FROM questions WHERE quiz_id = ?', (quiz_id,)).fetchall()

    if quiz is None:
        flash("Quiz not found.", "danger")
        conn.close()
        return redirect(url_for('student_dashboard'))

    if request.method == 'POST':
        score = 0
        total_questions = len(questions)

        for question in questions:
            # Get user's answer for each question
            user_answer = request.form.get(f'answer_{question["id"]}')
            correct_answer = question['correct_answer']

            # Debugging: Check the user input and correct answer in the console
            print(f"Question ID: {question['id']}, User Answer: {user_answer}, Correct Answer: {correct_answer}")

            # Ensure both user_answer and correct_answer are not None
            if user_answer is not None and correct_answer is not None:
                # Compare answers after stripping whitespace and converting to lowercase
                if user_answer.strip().lower() == correct_answer.strip().lower():
                    score += 1
                    print(f"Correct! Score: {score}")  # Debug print
                else:
                    print(f"Incorrect! Score: {score}")  # Debug print
            else:
                print(f"Missing answer or correct answer for question ID: {question['id']}")  # Debug print

        # Insert the quiz result into the database for the current user
        conn.execute('INSERT INTO quiz_results (user_id, quiz_id, score, total_questions) VALUES (?, ?, ?, ?)', 
                     (session['user_id'], quiz_id, score, total_questions))
        conn.commit()
        conn.close()

        # Redirect to results page after submitting the quiz
        flash(f"Quiz submitted successfully! Your score: {score}/{total_questions}", "success")
        return redirect(url_for('quiz_results'))

    conn.close()
    return render_template('take_quiz.html', quiz=quiz, questions=questions)


# Student results route
@app.route('/quiz_results')
def quiz_results():
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if user is None:
        flash("User not found. Please log in again.", "danger")
        conn.close()
        return redirect(url_for('login'))
    
    results = conn.execute('''
        SELECT qr.quiz_id, qr.score, q.title
        FROM quiz_results qr
        JOIN quizzes q ON qr.quiz_id = q.id
        WHERE qr.user_id = ?
    ''', (session['user_id'],)).fetchall()  # Fetch quiz results and titles for the user
    conn.close()

    return render_template('quiz_results.html', user=user, results=results)


# Login route
@app.route('/login', methods=['POST', 'GET'])
def login_post():
    if request.method == 'GET':
        return render_template('login.html')
    
    username = request.form['username']
    password = request.form['password']

    conn = get_db_connection()
    if conn is None:
        flash("Database connection failed. Please try again later.", "danger")
        return redirect(url_for('login'))

    user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()

    if user:
        # Store user information in the session
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']

        # Redirect the user to their respective dashboard after logging in
        if user['role'] == 'student':
            return redirect(url_for('student_dashboard'))
        elif user['role'] == 'educator':
            return redirect(url_for('educator_dashboard'))
    else:
        flash("Invalid credentials", "danger")
        return redirect(url_for('login'))


# Logout route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
