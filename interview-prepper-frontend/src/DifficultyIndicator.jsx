import React, { useState, useEffect } from 'react';
import './DifficultyIndicator.css';

/**
 * Component to display the current difficulty and handle changes
 */
const DifficultyIndicator = ({ 
  initialDifficulty = 'Easy', 
  onDifficultyChange = () => {},
  difficultyStats = null
}) => {
  const [difficulty, setDifficulty] = useState(initialDifficulty);
  const [isChanging, setIsChanging] = useState(false);
  const [hasChanged, setHasChanged] = useState(false);
  
  // Handle difficulty change
  useEffect(() => {
    if (isChanging) {
      // Animate the difficulty change
      const timer = setTimeout(() => {
        setIsChanging(false);
        setHasChanged(true);
      }, 1500);
      
      return () => clearTimeout(timer);
    }
  }, [isChanging]);
  
  // Update when difficulty changes
  const updateDifficulty = (newDifficulty, explanation) => {
    if (newDifficulty !== difficulty) {
      setDifficulty(newDifficulty);
      setIsChanging(true);
      
      // Callback to parent component
      onDifficultyChange(newDifficulty, explanation);
    }
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
  
  return (
    <div className={`difficulty-indicator ${isChanging ? 'changing' : ''}`}>
      <div className="difficulty-label">Difficulty:</div>
      <div 
        className="difficulty-level" 
        style={{ backgroundColor: getDifficultyColor(difficulty) }}
      >
        {difficulty}
      </div>
      
      {difficultyStats && (
        <div className="difficulty-stats">
          <div className="stats-item">
            <span>Started at:</span>
            <span style={{ color: getDifficultyColor(difficultyStats.original) }}>
              {difficultyStats.original}
            </span>
          </div>
          <div className="stats-item">
            <span>Ended at:</span>
            <span style={{ color: getDifficultyColor(difficultyStats.final) }}>
              {difficultyStats.final}
            </span>
          </div>
          <div className="stats-item">
            <span>Recommended:</span>
            <span style={{ color: getDifficultyColor(difficultyStats.recommended) }}>
              {difficultyStats.recommended}
            </span>
          </div>
          <div className="stats-item">
            <span>Average score:</span>
            <span>{difficultyStats.avg_score}/10</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default DifficultyIndicator;
