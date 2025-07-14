import { useState, useEffect, useRef } from "react";
import ConfirmationModal from "./ConfirmationModal";
import FeedbackHistory from "./FeedbackHistory";
import VoiceButton from "./voice-button";
import "./Modal.css";
import "./chat-controls.css";
import "./voice-button.css";

const Chat = ({ initialDifficulty = "Easy", isResumeUploaded = false }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [scoreInfo, setScoreInfo] = useState(null);
  const messagesEndRef = useRef(null);
  const [typingEffect, setTypingEffect] = useState(false);
  const [botResponse, setBotResponse] = useState("");
  const [typingIndex, setTypingIndex] = useState(0);
  const [isInterviewOver, setIsInterviewOver] = useState(false);
  
  // New state variables for confirmation modal
  const [showDifficultyModal, setShowDifficultyModal] = useState(false);
  const [pendingDifficulty, setPendingDifficulty] = useState(null);
  const [difficultyExplanation, setDifficultyExplanation] = useState("");
  const [currentDifficulty, setCurrentDifficulty] = useState("Easy");
  
  // New state for feedback history modal
  const [showFeedbackHistory, setShowFeedbackHistory] = useState(false);

  // Auto-scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Update current difficulty when initialDifficulty prop changes
  useEffect(() => {
    if (initialDifficulty) {
      setCurrentDifficulty(initialDifficulty);
    }
  }, [initialDifficulty]);
  
  // Show welcome message when resume is uploaded
  useEffect(() => {
    if (isResumeUploaded && messages.length === 0) {
      setMessages([
        {
          sender: "system",
          text: `📋 Resume uploaded. Starting with ${initialDifficulty} difficulty.`,
          id: `system-${Date.now()}`,
        }
      ]);
    }
  }, [isResumeUploaded, initialDifficulty, messages.length]);

  // Typing effect for bot messages
  useEffect(() => {
    if (typingEffect && typingIndex < botResponse.length) {
      const timer = setTimeout(() => {
        setTypingIndex(typingIndex + 1);
      }, 20); // Adjust speed here
      return () => clearTimeout(timer);
    } else if (typingEffect && typingIndex >= botResponse.length) {
      setTypingEffect(false);
      // Add the fully typed message to the messages array
      setMessages((prevMessages) => [
        ...prevMessages.filter((msg) => msg.id !== "typing"),
        { sender: "bot", text: botResponse, id: Date.now() },
      ]);
    }
  }, [typingEffect, typingIndex, botResponse]);

  // 🎤 Voice input using custom component that records audio and sends to backend
  const [isVoiceButtonDisabled, setIsVoiceButtonDisabled] = useState(false);
  
  // Handle transcription from the voice button component
  const handleTranscriptionReceived = (transcript, analysis) => {
    console.log("Received transcription:", transcript);
    console.log("Speech analysis:", analysis);
    
    // Handle error case
    if (!transcript) {
      // Check if we have an error message in the analysis
      const errorMessage = analysis && analysis.error ? analysis.error : "Unknown error";
      console.error("Transcription error:", errorMessage);
      
      // Add an error message to the chat
      setMessages((prevMessages) => [
        ...prevMessages,
        {
          sender: "system",
          text: `❌ Speech recognition failed: ${errorMessage}`,
          id: `transcription-error-${Date.now()}`,
          isError: true
        }
      ]);
      return;
    }
    
    // Set the input to the transcribed text
    setInput(transcript);
    
    // Add the transcription as a system message
    setMessages((prevMessages) => [
      ...prevMessages,
      {
        sender: "system",
        text: `🎤 Transcription: "${transcript}"`,
        id: `transcription-${Date.now()}`,
      }
    ]);
    
    // Add confidence analysis as a separate message
    if (analysis && analysis.confidence_score !== undefined) {
      setScoreInfo({
        score: analysis.confidence_score,
        feedback: analysis.confidence_feedback || "No detailed confidence feedback available."
      });
      
      // Determine emoji based on confidence score
      let confidenceEmoji = "📊";
      if (analysis.confidence_score >= 8) {
        confidenceEmoji = "🌟"; // Excellent
      } else if (analysis.confidence_score >= 6) {
        confidenceEmoji = "✅"; // Good
      } else if (analysis.confidence_score >= 4) {
        confidenceEmoji = "⚠️"; // Average
      } else {
        confidenceEmoji = "⚠️"; // Needs improvement
      }
      
      // Add confidence score message to chat
      setMessages((prevMessages) => [
        ...prevMessages,
        {
          sender: "system",
          text: `${confidenceEmoji} Confidence Score: ${analysis.confidence_score}/10`,
          id: `confidence-${Date.now()}`,
        }
      ]);
      
      // Add confidence feedback if available
      if (analysis.confidence_feedback) {
        setMessages((prevMessages) => [
          ...prevMessages,
          {
            sender: "system",
            text: `💬 ${analysis.confidence_feedback}`,
            id: `feedback-${Date.now()}`,
          }
        ]);
      }
      
      // Automatically send the transcription as a message to get the next question
      // This ensures the confidence data is already stored in the database
      console.log("Automatically sending transcribed message to get next question");
      setTimeout(() => {
        sendTranscribedMessage(transcript);
      }, 1000); // Small delay to ensure user sees the confidence score
    }
  };

  const sendMessage = async () => {
    if (!input.trim()) return;

    // Check if this is an exit command
    const isExitCommand = input.trim().toLowerCase() === "exit";

    const userMessage = { sender: "user", text: input, id: Date.now() };
    setMessages((prevMessages) => [...prevMessages, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const response = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          message: input,
          current_difficulty: currentDifficulty,
          user_id: "guest" // You can replace with actual user ID if available
        }),
      });

      const data = await response.json();

      // Debug logging
      console.log("Received data from backend:", data);
      console.log("Reply:", data.reply);

      // Mark interview as over if this was an exit command
      if (isExitCommand) {
        setIsInterviewOver(true);

        // Add a separator message to indicate end of interview
        setMessages((prevMessages) => [
          ...prevMessages,
          {
            sender: "system",
            text: "🏁 Interview Completed - Final Feedback",
            id: `system-${Date.now()}`,
          },
        ]);

        // If backend returns a qas array, format and display feedback summary
        if (Array.isArray(data.qas)) {
          // Format the feedback summary as a list
          const feedbackSummary = data.qas.map((qa, idx) => {
            return (
              `Q${idx + 1}: ${qa.question}\n` +
              `Your Answer: ${qa.answer}\n` +
              `Score: ${qa.score}/10` + (qa.confidence_score !== undefined ? `, Confidence: ${qa.confidence_score}/10` : "") + "\n" +
              (qa.feedback ? `Feedback: ${qa.feedback}\n` : "") +
              (qa.confidence_feedback ? `Confidence Feedback: ${qa.confidence_feedback}\n` : "") +
              (qa.difficulty ? `Difficulty: ${qa.difficulty}\n` : "") +
              (qa.timestamp ? `Time: ${qa.timestamp}\n` : "")
            );
          }).join("\n-----------------------------\n");

          setMessages((prevMessages) => [
            ...prevMessages,
            {
              sender: "bot",
              text: feedbackSummary,
              id: Date.now(),
              isFeedback: true
            },
          ]);
        } else {
          // Fallback: show reply if qas is not present
          setMessages((prevMessages) => [
            ...prevMessages,
            { 
              sender: "bot", 
              text: data.reply, 
              id: Date.now(),
              isFeedback: true 
            },
          ]);
        }
        
        // Add resume strengthening directly if available
        if (data.resume_strengthening) {
          console.log("Adding resume strengthening feedback immediately");
          // Add immediately without setTimeout to ensure it's displayed
          setMessages((prevMessages) => [
            ...prevMessages,
            {
              sender: "bot",
              text: "📝 **Resume Strengthening Suggestions:**\n" + data.resume_strengthening,
              id: Date.now() + 100,
              isResumeStrengthening: true,
            },
          ]);
          // Ensure we scroll to the bottom to show the resume feedback
          scrollToBottom();
        }
      } else {
        // For normal responses, use typing effect
        setBotResponse(data.reply);
        setTypingIndex(0);
        setTypingEffect(true);

        // Add temporary typing indicator
        setMessages((prevMessages) => [
          ...prevMessages,
          {
            sender: "bot",
            text: "",
            id: "typing",
            isTyping: true,
          },
        ]);
        
        // If we have score information
        if (data.score !== undefined) {
          setScoreInfo({
            score: data.score,
            feedback: data.feedback || "No detailed feedback available.",
          });
        }
        
        // Check if difficulty change is suggested
        if (data.suggested_difficulty) {
          // Store the suggested difficulty and explanation for confirmation modal
          setPendingDifficulty(data.suggested_difficulty);
          setDifficultyExplanation(data.difficulty_explanation || 
            `Based on your performance, the system suggests changing the difficulty to ${data.suggested_difficulty}.`);
          setShowDifficultyModal(true);
        }
        
        // For regular messages, add resume strengthening later if available
        if (data.resume_strengthening) {
          console.log("Adding resume strengthening as separate message");
          setTimeout(() => {
            setMessages((prevMessages) => [
              ...prevMessages,
              {
                sender: "bot",
                text: "📝 **Resume Strengthening Suggestions:**\n" + data.resume_strengthening,
                id: Date.now() + 100,
                isResumeStrengthening: true,
              },
            ]);
          }, 1000);
        }
      }
    } catch (error) {
      console.error("Error in sendMessage:", error);
      const errorMessage = {
        sender: "bot",
        text: "❌ Server error. Try again.",
        id: Date.now(),
        isError: true,
      };
      setMessages((prevMessages) => [...prevMessages, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  // Function to automatically send the transcribed message
  const sendTranscribedMessage = async (transcript) => {
    if (!transcript || !transcript.trim()) return;

    // Add the user message to the chat
    const userMessage = { sender: "user", text: transcript, id: Date.now() };
    setMessages((prevMessages) => [...prevMessages, userMessage]);
    setLoading(true);

    try {
      const response = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          message: transcript,
          current_difficulty: currentDifficulty,
          user_id: "guest"
        }),
      });

      const data = await response.json();
      console.log("Auto-send response:", data);

      // Handle confidence score returned from backend
      if (data.confidence_score !== undefined) {
        console.log(`Backend returned confidence score: ${data.confidence_score}`);
      }

      // Begin typing effect for the bot's response
      setBotResponse(data.reply || "Sorry, I didn't understand that.");
      setTypingIndex(0);
      setTypingEffect(true);

      // Add typing indicator
      setMessages((prevMessages) => [
        ...prevMessages,
        { sender: "typing", text: "", id: "typing" },
      ]);

      // Check if difficulty suggestion is included in response
      if (data.suggested_difficulty && data.suggested_difficulty !== currentDifficulty) {
        // Show confirmation modal with explanation
        setPendingDifficulty(data.suggested_difficulty);
        setDifficultyExplanation(data.difficulty_explanation || "");
        setShowDifficultyModal(true);
      }
    } catch (error) {
      console.error("Error in sendTranscribedMessage:", error);
      const errorMessage = {
        sender: "bot",
        text: "❌ Server error. Try again.",
        id: Date.now(),
        isError: true,
      };
      setMessages((prevMessages) => [...prevMessages, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  // Reset the interview state
  const resetInterview = () => {
    setMessages([]);
    setScoreInfo(null);
    setIsInterviewOver(false);
    setInput("");
    // Reset difficulty-related state
    setCurrentDifficulty("Easy");
    setPendingDifficulty(null);
  };
  
  // Handle difficulty confirmation
  const handleDifficultyConfirmation = async () => {
    // Update current difficulty
    setCurrentDifficulty(pendingDifficulty);
    
    // Add a system message about the difficulty change
    setMessages(prevMessages => [
      ...prevMessages,
      {
        sender: "system",
        text: `📊 Difficulty changed to ${pendingDifficulty}`,
        id: `difficulty-${Date.now()}`,
      }
    ]);
    
    // Close the modal and reset pending difficulty
    setShowDifficultyModal(false);
    setPendingDifficulty(null);
  };
  
  // Reject difficulty change
  const handleDifficultyRejection = () => {
    // Add a system message about rejecting the change
    setMessages(prevMessages => [
      ...prevMessages,
      {
        sender: "system",
        text: `📊 Difficulty remains at ${currentDifficulty}`,
        id: `difficulty-${Date.now()}`,
      }
    ]);
    
    // Close the modal and reset pending difficulty
    setShowDifficultyModal(false);
    setPendingDifficulty(null);
  };

  // Disable voice button when interview is over
  useEffect(() => {
    if (isInterviewOver) {
      setIsVoiceButtonDisabled(true);
    }
  }, [isInterviewOver]);

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h2>
          <i className="fas fa-comment-dots"></i> Interview Simulation
        </h2>
        <div className="header-controls">
          {!isInterviewOver && (
            <button 
              className="feedback-history-btn" 
              onClick={() => setShowFeedbackHistory(true)}
              title="View feedback history"
            >
              <i className="fas fa-history"></i>
            </button>
          )}
          <div className="difficulty-display">
            <span>Difficulty:</span>
            <div className={`difficulty-badge ${currentDifficulty.toLowerCase()}`}>
              {currentDifficulty}
            </div>
          </div>
          {scoreInfo && !isInterviewOver && (
            <div className="score-badge">
              <span>Last Score: {scoreInfo.score}/10</span>
            </div>
          )}
        </div>
      </div>

      {/* Confirmation Modal for Difficulty Changes */}
      <ConfirmationModal 
        isOpen={showDifficultyModal}
        onClose={handleDifficultyRejection}
        onConfirm={handleDifficultyConfirmation}
        title="Change Difficulty Level"
        message={difficultyExplanation}
        confirmText={`Change to ${pendingDifficulty}`}
        cancelText="Keep Current Difficulty"
      />
      
      {/* Feedback History Modal */}
      <FeedbackHistory 
        isOpen={showFeedbackHistory}
        onClose={() => setShowFeedbackHistory(false)}
      />

      <div className="messages">
        {messages.length === 0 ? (
          <div className="empty-chat">
            <div className="welcome-message">
              <i className="fas fa-robot robot-icon"></i>
              <h3>Welcome to Your Interview Coach!</h3>
              <p>Click "Start Interview" to begin your interview simulation.</p>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`message ${
                msg.sender === "user" ? "user" : "bot"
              } ${msg.isTyping ? "typing" : ""} ${
                msg.isError ? "error" : ""
              } ${msg.sender === "system" ? "system" : ""} ${
                msg.isResumeStrengthening ? "isResumeStrengthening" : ""
              } ${
                msg.isFeedback ? "isFeedback" : ""
              }`}
            >
              {msg.isTyping ? (
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              ) : (
                <>
                  {msg.sender === "bot" && (
                    <i className="fas fa-robot bot-icon"></i>
                  )}
                  {msg.sender === "user" && (
                    <i className="fas fa-user user-icon"></i>
                  )}
                  {msg.isResumeStrengthening && (
                    <i className="fas fa-file-alt resume-icon"></i>
                  )}
                  <span className="message-text">
                    {msg.isResumeStrengthening ? (
                      <>
                        <h4>📝 Resume Strengthening Suggestions:</h4>
                        <div className="resume-suggestions">
                          {msg.text.replace("📝 **Resume Strengthening Suggestions:**\n", "")}
                        </div>
                      </>
                    ) : (
                      msg.text
                    )}
                  </span>
                </>
              )}
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {scoreInfo && !isInterviewOver && (
        <div className="feedback-panel">
          <div className="feedback-header">
            <i className="fas fa-chart-bar"></i> Performance Feedback
            <button
              className="close-btn"
              onClick={() => setScoreInfo(null)}
            >
              ×
            </button>
          </div>
          <div className="feedback-content">
            <div className="score-display">
              <div
                className="score-circle"
                style={{
                  background: `conic-gradient(#4f2268 ${
                    scoreInfo.score * 10
                  }%, #e0e0e0 0)`,
                }}
              >
                <span>{scoreInfo.score}/10</span>
              </div>
            </div>
            <div className="feedback-text">{scoreInfo.feedback}</div>
          </div>
        </div>
      )}

      <div className="chat-input-group">
        <input
          type="text"
          className="chat-input"
          placeholder="Type a message or use voice..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          disabled={isInterviewOver}
        />
        <VoiceButton 
          onTranscriptionReceived={handleTranscriptionReceived}
          disabled={isInterviewOver || isVoiceButtonDisabled}
        />
        <button
          className="send-btn"
          onClick={sendMessage}
          disabled={loading || !input.trim() || isInterviewOver}
        >
          <i className="fas fa-paper-plane"></i>
        </button>
      </div>

      <div className="chat-actions">
        {!isInterviewOver ? (
          <>
            <button
              className="action-btn start-btn"
              onClick={() => {
                setInput("start");
                setTimeout(sendMessage, 100);
              }}
              disabled={loading}
            >
              <i className="fas fa-play"></i> Start Interview
            </button>
            <button
              className="action-btn exit-btn"
              onClick={() => {
                setInput("exit");
                setTimeout(sendMessage, 100);
              }}
              disabled={loading}
            >
              <i className="fas fa-door-open"></i> End Interview
            </button>
          </>
        ) : (
          <button
            className="action-btn restart-btn"
            onClick={resetInterview}
          >
            <i className="fas fa-redo"></i> Start New Interview
          </button>
        )}
      </div>
    </div>
  );
};

export default Chat;
