from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import os
import sqlite3
import fitz 
from werkzeug.utils import secure_filename
from groq import Groq
import json
import csv

app = Flask(__name__)
app.secret_key = 'borntodie'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
groq_client = Groq(api_key="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")# groq key


# text extract function
def extract_text_from_pdf(pdf_path):
  doc = fitz.open(pdf_path)
  text = ""
  for page in doc:
      text += page.get_text()
  doc.close()
  return text

# prompt function
def analyze_resume_with_groq(resume_text, job_role):

    prompt = f"""
    You are an HR expert analyzing a resume for the position: {job_role}

    Resume text:
    {resume_text[:2500]}

    Extract the following information and respond with ONLY a valid JSON object:

    {{
        "name": "Full Name Here",
        "skills": "skill1, skill2, skill3, skill4, skill5",
        "experience": "X years experience in relevant field at Y company with specific achievements",
        "match_percentage": 75
    }}

    Requirements:
    - name: Extract the candidate's full name (first and last name)
    - skills: List exactly 5-8 relevant skills separated by commas
    - experience: Write 1-2 sentences about their work experience along with company name, duration, role, achievements and college name if applicable.
    - match_percentage: Rate 0-100 based on how well they fit the {job_role} role

    Return ONLY the JSON object, no explanations.
    """

    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="meta-llama/llama-4-maverick-17b-128e-instruct",
        temperature=0.2,
    )

    response_text = response.choices[0].message.content.strip()

    if not response_text:
        raise ValueError("Groq returned an empty response")


    if response_text.startswith("```"):
        response_text = (
            response_text
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        print("Groq returned invalid JSON:")
        print(response_text)
        raise ValueError("Invalid JSON response from Groq")

    result = {
        'name': str(data.get('name', '')).strip(),
        'skills': str(data.get('skills', '')).strip(),
        'experience': str(data.get('experience', '')).strip(),
        'match_percentage': int(data.get('match_percentage', 0))
    }

    return result

# Home redirector
@app.route('/')
def index():
  if 'logged_in' not in session:
      return redirect(url_for('login'))
  return redirect(url_for('upload'))

#Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'logged_in' in session:
        return redirect(url_for('upload'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check credentials
        if username == 'admin' and password == 'admin123':
            session['logged_in'] = True
            return redirect(url_for('upload'))
        else:
            flash("Invalid username or password.", "error")
            return redirect(url_for('login'))

    return render_template('login.html')


# Logout
@app.route('/logout')
def logout():
  session.pop('logged_in', None)
  return redirect(url_for('login'))

# Uploadpage
@app.route('/upload', methods=['GET', 'POST'])
def upload():
  if 'logged_in' not in session:
      return redirect(url_for('login'))
  
  if request.method == 'POST':
      job_role = request.form['job_role']
      file = request.files['resume']
      
      if not job_role:
          return redirect(url_for('upload'))
      
      if not file or file.filename == '':
          return redirect(url_for('upload'))
      
      if file and file.filename.endswith('.pdf'):
          filename = secure_filename(file.filename)
          filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
          file.save(filepath)
          
          
          resume_text = extract_text_from_pdf(filepath)
          
          if resume_text:
              
              groq_analysis = analyze_resume_with_groq(resume_text, job_role)
              
              if groq_analysis:
                  is_shortlisted = 0
                  
                  conn = sqlite3.connect('hirescope.db')
                  cursor = conn.cursor()
                 
                  cursor.execute('''
                      INSERT INTO candidates 
                      (name, skills, experience, job_role, resume_text, match_percentage, filename, is_shortlisted)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                  ''', (
                      groq_analysis['name'],
                      groq_analysis['skills'],
                      groq_analysis['experience'],
                      job_role,
                      resume_text[:3000],
                      groq_analysis['match_percentage'],
                      filename,
                      is_shortlisted
                  ))
                  
                  conn.commit()
                  conn.close()
          
        
      
      return redirect(url_for('candidates'))
  
  return render_template('upload.html')

# Candidate Page
@app.route('/candidates')
def candidates():
  if 'logged_in' not in session:
      return redirect(url_for('login'))
  
  conn = sqlite3.connect('hirescope.db')
  cursor = conn.cursor()

  job_role_filter = request.args.get('job_role')
  sort_by = request.args.get('sort_by')

  query = "SELECT * FROM candidates"
  params = []

  if job_role_filter and job_role_filter != 'all':
      query += " WHERE job_role = ?"
      params.append(job_role_filter)
 
  if sort_by == 'match_desc':
      query += " ORDER BY match_percentage DESC"
  elif sort_by == 'match_asc':
      query += " ORDER BY match_percentage ASC"
  elif sort_by == 'date_desc':
      query += " ORDER BY created_at DESC"
  elif sort_by == 'date_asc':
      query += " ORDER BY created_at ASC"
  else: 
      query += " ORDER BY match_percentage DESC"

  cursor.execute(query, params)
  candidates_data = cursor.fetchall()

  # Job role fetching
  cursor.execute("SELECT DISTINCT job_role FROM candidates ORDER BY job_role ASC")
  job_roles = [row[0] for row in cursor.fetchall()]
  
  conn.close()
  
  return render_template('candidates.html',candidates=candidates_data, job_roles=job_roles, selected_job_role=job_role_filter, selected_sort_by=sort_by)
  
# Shortlisted 
@app.route('/shortlist/<int:candidate_id>')
def toggle_shortlist(candidate_id):
  if 'logged_in' not in session:
      return redirect(url_for('login'))
  
  conn = sqlite3.connect('hirescope.db')
  cursor = conn.cursor()
  
  # Fetch candidate data
  cursor.execute('SELECT is_shortlisted, name FROM candidates WHERE id = ?', (candidate_id,))
  result = cursor.fetchone()
  
  if result:
      current_status, name = result
      new_status = 0 if current_status else 1
      
      # Update status
      cursor.execute('UPDATE candidates SET is_shortlisted = ? WHERE id = ?', (new_status, candidate_id))
      conn.commit()
  
  conn.close()
  return redirect(url_for('candidates'))

#Delete route 
@app.route('/delete/<int:candidate_id>', methods=['POST'])
def delete_candidate(candidate_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('hirescope.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM candidates WHERE id = ?', (candidate_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('candidates'))


# Shortlisted Page
@app.route('/shortlisted')
def shortlisted():
  if 'logged_in' not in session:
      return redirect(url_for('login'))
  
  conn = sqlite3.connect('hirescope.db')
  cursor = conn.cursor()

  job_role_filter = request.args.get('job_role')
  sort_by = request.args.get('sort_by')

  query = "SELECT * FROM candidates WHERE is_shortlisted = 1"
  params = []

  if job_role_filter and job_role_filter != 'all':
      query += " AND job_role = ?"
      params.append(job_role_filter)

  if sort_by == 'match_desc':
      query += " ORDER BY match_percentage DESC"
  elif sort_by == 'match_asc':
      query += " ORDER BY match_percentage ASC"
  elif sort_by == 'date_desc':
      query += " ORDER BY created_at DESC"
  elif sort_by == 'date_asc':
      query += " ORDER BY created_at ASC"
  else: 
      query += " ORDER BY match_percentage DESC"

  cursor.execute(query, params)
  candidates_data = cursor.fetchall()

  # job role fetching
  cursor.execute("SELECT DISTINCT job_role FROM candidates WHERE is_shortlisted = 1 ORDER BY job_role ASC")
  job_roles = [row[0] for row in cursor.fetchall()]
  
  conn.close()
  
  return render_template('shortlisted.html', candidates=candidates_data, job_roles=job_roles, selected_job_role=job_role_filter, selected_sort_by=sort_by)

@app.route('/download_shortlisted')
def download_shortlisted():
    conn = sqlite3.connect('hirescope.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name, skills, experience, job_role, match_percentage, filename, created_at FROM candidates WHERE is_shortlisted = 1")
    rows = cursor.fetchall()
    conn.close()

    file_path = "shortlisted_candidates.csv"
    with open(file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Name", "Skills", "Experience", "Job Role", "Match %", "Resume Filename", "Created At"])
        writer.writerows(rows)

    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
  if not os.path.exists('hirescope.db'):
      exit(1)
  
  app.run(debug=True)
