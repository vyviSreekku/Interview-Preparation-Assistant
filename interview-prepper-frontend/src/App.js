import React, { useState, useEffect } from "react";
import Chat from "./chat";
import "./App.css";

function App() {
  const [darkMode, setDarkMode] = useState(false);
  const [resumeFile, setResumeFile] = useState(null);
  const [jobDescription, setJobDescription] = useState("");
  const [difficulty, setDifficulty] = useState("Easy");
  const [uploadStatus, setUploadStatus] = useState("");
  const [isUploaded, setIsUploaded] = useState(false);
  const [fileName, setFileName] = useState("");
  const [isUploadPanelOpen, setIsUploadPanelOpen] = useState(true);

  useEffect(() => {
    // Check for user's preferred color scheme
    const prefersDarkMode = window.matchMedia("(prefers-color-scheme: dark)").matches;
    setDarkMode(localStorage.getItem("darkMode") === "true" || prefersDarkMode);
    
    // Add FontAwesome dynamically
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css';
    document.head.appendChild(link);
    
    return () => {
      document.head.removeChild(link);
    };
  }, []);

  useEffect(() => {
    if (darkMode) {
      document.body.classList.add("dark");
    } else {
      document.body.classList.remove("dark");
    }
    localStorage.setItem("darkMode", darkMode);
  }, [darkMode]);

  const toggleMode = () => {
    setDarkMode(!darkMode);
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setResumeFile(file);
      setFileName(file.name);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!resumeFile) {
      setUploadStatus("❌ Please select a resume file.");
      return;
    }

    setUploadStatus("⏳ Uploading...");
    
    const formData = new FormData();
    formData.append("resume", resumeFile);
    formData.append("job_description", jobDescription);
    formData.append("difficulty", difficulty);

    try {
      const response = await fetch("http://localhost:8000/upload_resume", {
        method: "POST",
        body: formData
      });

      const data = await response.json();
      if (response.ok) {
        setUploadStatus("✅ Resume uploaded successfully!");
        setIsUploaded(true);
        
        // Auto collapse the upload panel after successful upload
        setTimeout(() => {
          setIsUploadPanelOpen(false);
        }, 1500);
      } else {
        setUploadStatus("❌ Upload failed: " + data.error);
      }
    } catch (error) {
      setUploadStatus("❌ Error uploading resume.");
    }
  };
  
  const toggleUploadPanel = () => {
    setIsUploadPanelOpen(!isUploadPanelOpen);
  };

  return (
    <div className="app-container">
      <div className="background-gradient"></div>
      
      <nav className="navbar">
        <h1 className="logo">
          <i className="fas fa-robot"></i> Interview Prepper
        </h1>
        <div className="navbar-right">
          <button className="btn toggle-mode-btn" onClick={toggleMode} aria-label="Toggle dark mode">
            <i className={`fas ${darkMode ? "fa-sun" : "fa-moon"}`}></i>
          </button>
        </div>
      </nav>

      <div className="title-section">
        <h1>Your AI Interview Coach</h1>
        <p>Practice interviews with personalized feedback and resume analysis</p>
      </div>

      <div className="main-container">
        <Chat initialDifficulty={difficulty} isResumeUploaded={isUploaded} />

        <div className={`upload-panel ${isUploadPanelOpen ? "open" : "closed"}`}>
          <div className="panel-toggle" onClick={toggleUploadPanel}>
            {isUploadPanelOpen ? (
              <><i className="fas fa-chevron-right"></i> Hide</>
            ) : (
              <><i className="fas fa-chevron-left"></i> Setup</>
            )}
          </div>
          
          <div className="panel-content">
            <h2><i className="fas fa-cog"></i> Interview Setup</h2>
            
            <form onSubmit={handleSubmit} className="upload-form">
              <div className="form-section">
                <h3><i className="fas fa-file-upload"></i> Upload Resume</h3>
                <div className="file-drop-area">
                  <input
                    type="file"
                    id="resume-upload"
                    className="file-input"
                    onChange={handleFileChange}
                    accept=".pdf,.doc,.docx"
                  />
                  <label htmlFor="resume-upload" className="file-label">
                    {fileName ? (
                      <div className="file-info">
                        <i className="fas fa-file-pdf"></i>
                        <span>{fileName}</span>
                      </div>
                    ) : (
                      <>
                        <i className="fas fa-cloud-upload-alt"></i>
                        <span>Choose a file or drag it here</span>
                      </>
                    )}
                  </label>
                </div>
              </div>

              <div className="form-section">
                <h3><i className="fas fa-briefcase"></i> Job Description</h3>
                <textarea
                  className="job-input"
                  placeholder="Paste job description for more targeted questions..."
                  value={jobDescription}
                  onChange={(e) => setJobDescription(e.target.value)}
                />
              </div>

              <div className="form-section">
                <h3><i className="fas fa-tachometer-alt"></i> Difficulty Level</h3>
                <div className="difficulty-selector">
                  {["Easy", "Medium", "Hard"].map((level) => (
                    <div 
                      key={level}
                      className={`difficulty-option ${difficulty === level ? "selected" : ""}`}
                      onClick={() => setDifficulty(level)}
                    >
                      <span>{level}</span>
                      <div className="difficulty-meter">
                        <div className={`difficulty-bar ${level.toLowerCase()}`}></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="form-actions">
                <button 
                  type="submit" 
                  className={`btn submit-btn ${isUploaded ? "success" : ""}`}
                  disabled={!resumeFile}
                >
                  {isUploaded ? (
                    <><i className="fas fa-check"></i> Ready</>
                  ) : (
                    <><i className="fas fa-upload"></i> Upload & Start</>
                  )}
                </button>
                {uploadStatus && <p className="status-message">{uploadStatus}</p>}
              </div>
            </form>
          </div>
        </div>
      </div>
      
      <footer className="app-footer">
        <p>© 2025 Interview Prepper | AI-Powered Interview Simulation</p>
      </footer>
    </div>
  );
}

export default App;
