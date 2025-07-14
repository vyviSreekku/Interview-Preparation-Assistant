import React, { useState, useEffect } from 'react';

/**
 * Component to display feedback history for all answered questions
 */
const FeedbackHistory = ({ isOpen, onClose }) => {
  const [feedbackData, setFeedbackData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    if (isOpen) {
      fetchFeedback();
    }
  }, [isOpen]);
  
  const fetchFeedback = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:8000/get_feedback');
      const data = await response.json();
      
      if (data.success) {
        setFeedbackData(data.feedback);
      } else {
        setError('Failed to load feedback data');
      }
    } catch (err) {
      setError(`Error loading feedback: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  // Helper to format timestamp
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'Unknown';
    const date = new Date(timestamp);
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric', 
      hour: '2-digit', 
      minute: '2-digit'
    }).format(date);
  };
  
  // Get color for difficulty level
  const getDifficultyColor = (level) => {
    switch (level) {
      case 'Easy':
        return '#4caf50'; // Green
      case 'Medium':
        return '#ff9800'; // Orange
      case 'Hard':
        return '#f44336'; // Red
      default:
        return '#2196f3'; // Blue
    }
  };
  
  if (!isOpen) return null;
  
  return (
    <div className="modal-overlay">
      <div className="modal-container feedback-history-modal">
        <div className="modal-header">
          <h3><i className="fas fa-history"></i> Feedback History</h3>
          <button className="modal-close-btn" onClick={onClose}>×</button>
        </div>
        
        <div className="modal-content feedback-history-content">
          {loading ? (
            <div className="loading-indicator">
              <i className="fas fa-spinner fa-spin"></i> Loading feedback...
            </div>
          ) : error ? (
            <div className="error-message">
              <i className="fas fa-exclamation-triangle"></i> {error}
            </div>
          ) : feedbackData.length === 0 ? (
            <div className="empty-feedback">
              <i className="fas fa-inbox"></i>
              <p>No feedback history available yet</p>
            </div>
          ) : (
            <div className="feedback-list">
              {feedbackData.map((item, index) => (
                <div key={index} className="feedback-item">
                  <div className="feedback-item-header">
                    <div className="feedback-time">
                      <i className="fas fa-clock"></i> {formatTimestamp(item.timestamp)}
                    </div>
                    <div 
                      className="feedback-difficulty" 
                      style={{ backgroundColor: getDifficultyColor(item.difficulty) }}
                    >
                      {item.difficulty}
                    </div>
                    <div className="feedback-score">
                      <span>Score:</span> {item.score}/10
                    </div>
                    {item.confidence_score !== undefined && (
                      <div className="feedback-confidence-score">
                        <span>Confidence:</span> {item.confidence_score}/10
                      </div>
                    )}
                  </div>
                  
                  <div className="feedback-qa">
                    <div className="feedback-question">
                      <span className="label">Q:</span> {item.question}
                    </div>
                    <div className="feedback-answer">
                      <span className="label">A:</span> {item.answer}
                    </div>
                  </div>
                  
                  <div className="feedback-details">
                    <div className="feedback-text">
                      <strong>Content Feedback:</strong> {item.feedback}
                    </div>
                    
                    {item.confidence_feedback && (
                      <div className="confidence-feedback-text">
                        <strong>Speech Confidence Feedback:</strong> {item.confidence_feedback}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default FeedbackHistory;
