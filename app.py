import streamlit as st
import google.generativeai as genai
import os
import PyPDF2 as pdf
from dotenv import load_dotenv
import json
import requests

# Load environment variables
load_dotenv()

# Configure Gemini AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Function to extract text from PDF
def input_pdf_text(uploaded_file):
    reader = pdf.PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        extracted_text = page.extract_text() or ""  # Handle None case
        text += extracted_text
    return text.strip()

# Function to get AI response
def get_gemini_response(input_text, jd):
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    Act as a highly experienced ATS (Applicant Tracking System) specializing in software engineering,
    data science, data analytics, and big data roles. Evaluate the resume against the provided job description.
    Consider that the job market is competitive and provide insights for improvement.

    Resume: {input_text}
    Job Description: {jd}

    You must respond with ONLY a valid JSON object and nothing else. No markdown, no extra text.
    The JSON should have this exact structure:
    {{
      "JD Match": "X%",
      "MissingKeywords": ["keyword1", "keyword2", "..."],
      "MatchedKeywords": ["keyword1", "keyword2", "..."],
      "ProfileSummary": "detailed summary here",
      "StrengthAreas": ["strength1", "strength2", "..."],
      "ImprovementAreas": ["area1", "area2", "..."],
      "RecommendedSkills": ["skill1", "skill2", "..."]
    }}
    """
    
    response = model.generate_content(prompt)
    
    try:
        # Clean the response text by removing any non-JSON content
        response_text = response.text.strip()
        # If response is wrapped in markdown code blocks, remove them
        if response_text.startswith("```json") and response_text.endswith("```"):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith("```") and response_text.endswith("```"):
            response_text = response_text[3:-3].strip()
            
        return json.loads(response_text)  # Convert AI response to JSON
    except Exception as e:
        if st.session_state.get('debug_mode', False):
            return {
                "error": f"Failed to process the response: {str(e)}",
                "raw_response": response.text
            }
        else:
            return {"error": "Failed to process the response. Please try again."}

# Page configuration
st.set_page_config(
    page_title="RecruitEase | ATS Resume Analyzer",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    /* Main theme colors */
    :root {
        --main-blue: #1E88E5;
        --light-blue: #BBD9F2;
        --dark-blue: #0D47A1;
        --accent-blue: #64B5F6;
    }
    
    /* Text and Headers */
    h1, h2, h3 {
        color: var(--dark-blue);
        font-family: 'Helvetica Neue', sans-serif;
    }
    
    /* Header styling */
    .main-header {
        background-color: var(--main-blue);
        padding: 1.5rem;
        border-radius: 10px;
        color: white !important;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* Card styling */
    .card {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
    }
    
    /* Input fields */
    .stTextInput, .stTextArea {
        border-radius: 8px;
    }
    
    /* Buttons */
    .stButton>button {
        background-color: var(--main-blue);
        color: white;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: bold;
        border: none;
        transition: all 0.3s;
        width: 100%;
    }
    
    .stButton>button:hover {
        background-color: var(--dark-blue);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }

    /* Result sections */
    .result-section {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border-left: 5px solid var(--main-blue);
    }
    
    /* Keyword pills */
    .keyword-pill {
        display: inline-block;
        padding: 5px 12px;
        margin: 5px;
        background-color: var(--light-blue);
        color: var(--dark-blue);
        border-radius: 20px;
        font-size: 14px;
        font-weight: 500;
    }
    
    /* Matched keyword pills */
    .matched-keyword {
        background-color: #c8e6c9;
        color: #2e7d32;
    }

    /* Section headers */
    .section-header {
        font-size: 1.2rem;
        font-weight: 600;
        color: var(--dark-blue);
        margin-bottom: 15px;
        border-bottom: 2px solid var(--accent-blue);
        padding-bottom: 8px;
    }
    
    /* Icon styling */
    .icon {
        vertical-align: middle;
        margin-right: 8px;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        color: #6c757d;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid #dee2e6;
    }
    
    /* File uploader */
    .css-1qrvfrg {
        background-color: var(--light-blue);
        border-radius: 10px;
        padding: 10px;
    }
    
    /* Progress bar */
    .match-progress {
        height: 20px;
        border-radius: 5px;
        background-color: #e9ecef;
        margin-top: 10px;
        margin-bottom: 20px;
        overflow: hidden;
    }
    
    .match-progress-bar {
        height: 100%;
        text-align: center;
        color: white;
        font-weight: bold;
        line-height: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'debug_mode' not in st.session_state:
    st.session_state['debug_mode'] = False
if 'analysis_complete' not in st.session_state:
    st.session_state['analysis_complete'] = False
if 'result' not in st.session_state:
    st.session_state['result'] = None

# Sidebar content
with st.sidebar:
    st.image("https://via.placeholder.com/150x80?text=RecruitEase", width=150)
    st.markdown("## Settings & Tips")
    
    # Settings
    st.markdown("### ⚙️ Settings")
    st.session_state['debug_mode'] = st.checkbox("Enable Debug Mode", st.session_state['debug_mode'])
    
    # Resume tips
    st.markdown("### 📝 Resume Tips")
    st.markdown("""
    - Tailor your resume to the job description
    - Quantify your achievements with numbers
    - Use action verbs (Led, Developed, Implemented)
    - Include relevant keywords from the job posting
    - Keep your resume concise and well-formatted
    """)
    
    # About section
    st.markdown("### ℹ️ About RecruitEase")
    st.markdown("""
    RecruitEase helps you optimize your resume for ATS systems using advanced AI analysis. Upload your resume, paste the job description, and get instant feedback.
    """)
    
    # Footer
    st.markdown("<div class='footer'>© 2025 RecruitEase | v1.0</div>", unsafe_allow_html=True)

# Main content
st.markdown("<h1 class='main-header'>📝 RecruitEase: ATS Resume Analyzer</h1>", unsafe_allow_html=True)

# Introduction
st.markdown("<div class='card'>", unsafe_allow_html=True)
st.markdown("""
### Welcome to RecruitEase! 
Our AI-powered tool analyzes your resume against job descriptions and provides actionable feedback to increase your chances of getting past ATS systems and landing that interview.
""")
st.markdown("</div>", unsafe_allow_html=True)

# Input section
st.markdown("<h2>📋 Upload & Analyze</h2>", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<p class='section-header'>📄 Job Description</p>", unsafe_allow_html=True)
    jd = st.text_area("Paste the job description here", height=250, placeholder="Paste the complete job description here...")
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<p class='section-header'>📎 Resume Upload</p>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload your resume (PDF format)", type="pdf", help="Please upload a PDF file only")
    
    if uploaded_file:
        st.success(f"File uploaded: {uploaded_file.name}")
        st.info("Your resume will be analyzed against the job description. Make sure both are complete for the best results.")
    st.markdown("</div>", unsafe_allow_html=True)

# Analyze button
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    analyze_button = st.button("🔍 Analyze My Resume")

# Processing and Results
if analyze_button:
    if uploaded_file is not None and jd.strip():
        with st.spinner("⏳ Analyzing your resume against the job description..."):
            # Extract text from resume
            resume_text = input_pdf_text(uploaded_file)
            
            # Get analysis from AI
            response = get_gemini_response(resume_text, jd)
            st.session_state['result'] = response
            st.session_state['analysis_complete'] = True
    else:
        st.error("Please upload your resume and enter a job description to proceed with the analysis.")

# Display results if analysis is complete
if st.session_state['analysis_complete'] and st.session_state['result']:
    response = st.session_state['result']
    
    if "error" in response:
        st.error(response["error"])
        
        # Show raw response in debug mode
        if st.session_state['debug_mode'] and "raw_response" in response:
            st.subheader("Raw AI Response")
            st.code(response["raw_response"])
            
            # Provide troubleshooting help
            st.subheader("Troubleshooting Tips")
            st.markdown("""
            - The AI response is not in valid JSON format
            - Try simplifying your resume or job description
            - Check if your API key is valid and has necessary permissions
            - Try again later as the service might be experiencing high traffic
            """)
    else:
        st.markdown("<h2>📊 Analysis Results</h2>", unsafe_allow_html=True)
        
        # Results overview
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            # Match percentage with progress bar
            match_percentage = int(response['JD Match'].strip('%'))
            st.markdown(f"<h2 style='text-align: center;'>Match Score</h2>", unsafe_allow_html=True)
            st.markdown(f"<h1 style='text-align: center; color: {'#28a745' if match_percentage >= 70 else '#ffc107' if match_percentage >= 40 else '#dc3545'};'>{response['JD Match']}</h1>", unsafe_allow_html=True)
            
            # Progress bar
            progress_color = '#28a745' if match_percentage >= 70 else '#ffc107' if match_percentage >= 40 else '#dc3545'
            st.markdown(f"""
            <div class='match-progress'>
                <div class='match-progress-bar' style='width: {match_percentage}%; background-color: {progress_color};'>
                    {match_percentage}%
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Quick assessment based on match percentage
            if match_percentage >= 70:
                st.success("Great match! Your resume is well-aligned with this position.")
            elif match_percentage >= 40:
                st.warning("Moderate match. Consider enhancing your resume with the suggested improvements.")
            else:
                st.error("Low match. Significant improvements needed to increase your chances.")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            # Strengths and improvement areas
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("<p class='section-header'>💪 Your Strengths</p>", unsafe_allow_html=True)
            for strength in response.get('StrengthAreas', []):
                st.markdown(f"✅ {strength}")
                
            st.markdown("<p class='section-header' style='margin-top: 20px;'>🔧 Areas for Improvement</p>", unsafe_allow_html=True)
            for area in response.get('ImprovementAreas', []):
                st.markdown(f"⚠️ {area}")
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Keywords section
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("<p class='section-header'>❌ Missing Keywords</p>", unsafe_allow_html=True)
            if response.get('MissingKeywords'):
                for keyword in response.get('MissingKeywords', []):
                    st.markdown(f"<span class='keyword-pill'>🔍 {keyword}</span>", unsafe_allow_html=True)
            else:
                st.info("No critical missing keywords detected!")
                
        with col2:
            st.markdown("<p class='section-header'>✅ Matched Keywords</p>", unsafe_allow_html=True)
            if response.get('MatchedKeywords'):
                for keyword in response.get('MatchedKeywords', []):
                    st.markdown(f"<span class='keyword-pill matched-keyword'>✓ {keyword}</span>", unsafe_allow_html=True)
            else:
                st.info("No matched keywords found.")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Profile summary
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<p class='section-header'>📋 Profile Summary</p>", unsafe_allow_html=True)
        st.markdown(f"{response.get('ProfileSummary', 'No profile summary available.')}")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Recommended skills
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<p class='section-header'>🚀 Recommended Skills</p>", unsafe_allow_html=True)
        st.markdown("Consider adding these skills to your resume to increase your match rate:")
        
        skill_cols = st.columns(3)
        for i, skill in enumerate(response.get('RecommendedSkills', [])):
            with skill_cols[i % 3]:
                st.markdown(f"<div style='background-color: #e9f5fe; padding: 10px; border-radius: 8px; margin: 5px 0;'><b>🔹 {skill}</b></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Action plan
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<p class='section-header'>📝 Your Action Plan</p>", unsafe_allow_html=True)
        st.markdown("""
        1. **Add Missing Keywords**: Include the missing keywords highlighted above where relevant in your resume.
        2. **Quantify Achievements**: Add specific metrics and numbers to demonstrate your impact.
        3. **Optimize Format**: Ensure your resume is ATS-friendly with a clean, simple format.
        4. **Tailor Your Summary**: Customize your professional summary to match this specific role.
        5. **Add Recommended Skills**: Incorporate relevant skills you possess but haven't mentioned.
        """)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # In debug mode, show the raw response
        if st.session_state['debug_mode']:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("<p class='section-header'>🛠️ Debug Information</p>", unsafe_allow_html=True)
            st.json(response)
            st.markdown("</div>", unsafe_allow_html=True)
            
        # Reset button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("📝 Analyze Another Resume"):
                st.session_state['analysis_complete'] = False
                st.session_state['result'] = None
