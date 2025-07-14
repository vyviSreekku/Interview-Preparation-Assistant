import React, { useState, useRef, useEffect } from 'react';
import './voice-button.css';

const VoiceButton = ({ onTranscriptionReceived, disabled = false }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioLevel, setAudioLevel] = useState(0);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);
  const analyserRef = useRef(null);
  const animationRef = useRef(null);

  // Update recording time counter
  useEffect(() => {
    if (isRecording) {
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    }
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [isRecording]);

  // Format time as MM:SS
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Visualize audio levels
  const updateAudioLevel = () => {
    if (!analyserRef.current || !isRecording) return;
    
    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    analyserRef.current.getByteFrequencyData(dataArray);
    
    // Calculate average volume level
    const average = dataArray.reduce((acc, val) => acc + val, 0) / dataArray.length;
    setAudioLevel(average);
    
    // Continue animation loop
    animationRef.current = requestAnimationFrame(updateAudioLevel);
  };

  const startRecording = async () => {
    try {
      console.log("Requesting microphone access...");
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          // Request higher quality audio
          sampleRate: 44100,
          sampleSize: 16,
          channelCount: 1
        } 
      });
      
      console.log("Microphone access granted");
      
      // Set up audio analyzer for visualizing audio levels
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 512; // Increased for better resolution
      source.connect(analyser);
      analyserRef.current = analyser;
      
      // Start visualization
      animationRef.current = requestAnimationFrame(updateAudioLevel);
      
      // Reset recording time
      setRecordingTime(0);
      
      // Determine the best audio format the browser supports - prioritize better formats first
      let mimeType = 'audio/webm';
      const supportedTypes = [
        'audio/webm;codecs=opus', // Opus codec provides best speech quality
        'audio/wav', 
        'audio/mp4',
        'audio/webm',
        'audio/ogg'
      ];
      
      for (const type of supportedTypes) {
        if (MediaRecorder.isTypeSupported(type)) {
          mimeType = type;
          console.log(`Using supported MIME type: ${mimeType}`);
          break;
        }
      }
      
      // Create a new MediaRecorder with options for better audio quality
      const options = { 
        mimeType: mimeType,
        audioBitsPerSecond: 256000 // Higher bitrate for better quality
      };
      
      const mediaRecorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];
      
      // Handle data available event - log more detail for debugging
      mediaRecorder.ondataavailable = (e) => {
        console.log(`Data available event: ${e.data.size} bytes, type: ${e.data.type}`);
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
          
          // Log cumulative recording size
          const totalSize = audioChunksRef.current.reduce((sum, chunk) => sum + chunk.size, 0);
          console.log(`Total recorded data so far: ${(totalSize / 1024).toFixed(2)} KB`);
        } else {
          console.warn("Received empty data chunk");
        }
      };
      
      // Set up error handler with more detailed logging
      mediaRecorder.onerror = (event) => {
        console.error("Media recorder error:", event.error);
        console.error("Error name:", event.error.name);
        console.error("Error message:", event.error.message);
        alert(`Recording error: ${event.error.message || "Unknown error"}`);
        setIsRecording(false);
      };
      
      // Monitor state changes for debugging
      mediaRecorder.onstart = () => console.log("MediaRecorder started");
      mediaRecorder.onpause = () => console.log("MediaRecorder paused");
      mediaRecorder.onresume = () => console.log("MediaRecorder resumed");
      mediaRecorder.onstop = () => console.log("MediaRecorder stopped natively");
      
      // Start recording with a smaller timeslice for more frequent chunks
      mediaRecorder.start(250); // Get data every 250ms for more responsive updates
      setIsRecording(true);
      
      console.log("Recording started with settings:", options);
      
      // Safety timeout - stop recording after 3 minutes if not stopped manually (increased from 2 minutes)
      setTimeout(() => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
          console.log("Safety timeout: stopping recording after 3 minutes");
          stopRecording();
        }
      }, 180000); // 3 minutes
    } catch (err) {
      console.error("Error starting recording:", err);
      
      // Provide more helpful error messages
      if (err.name === 'NotAllowedError') {
        alert("Microphone access denied. Please allow microphone access in your browser settings and try again.");
      } else if (err.name === 'NotFoundError') {
        alert("No microphone found. Please connect a microphone and try again.");
      } else {
        alert(`Could not access microphone: ${err.message}. Please check your device settings.`);
      }
    }
  };

  const stopRecording = () => {
    if (!mediaRecorderRef.current || mediaRecorderRef.current.state === "inactive") {
      console.log("No active recording to stop");
      return;
    }
    
    console.log("Stopping recording...");
    
    // Cancel animation frame
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }
    
    // Request a final data chunk before stopping
    console.log("Requesting final data chunk");
    mediaRecorderRef.current.requestData();
    
    // Set up the onstop handler before stopping
    mediaRecorderRef.current.onstop = async () => {
      try {
        setIsProcessing(true);
        
        // Check if we have audio data
        if (!audioChunksRef.current.length) {
          throw new Error("No audio data recorded");
        }
        
        console.log(`Audio recording stopped. Collected ${audioChunksRef.current.length} chunks`);
        
        // Extended delay to ensure ALL audio data is collected and processed by the browser
        console.log("Waiting to ensure all audio data is collected...");
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Log details of each chunk
        audioChunksRef.current.forEach((chunk, index) => {
          console.log(`Chunk ${index+1}: ${(chunk.size / 1024).toFixed(2)} KB, type: ${chunk.type}`);
        });
        
        // Create blob from audio chunks with the correct mime type
        // Try to use the correct mime type from the chunks if available
        const chunkType = audioChunksRef.current[0]?.type || 'audio/wav';
        const audioBlob = new Blob(audioChunksRef.current, { type: chunkType });
        console.log(`Audio blob created: ${(audioBlob.size / 1024).toFixed(2)} KB, type: ${audioBlob.type}`);
        
        if (audioBlob.size === 0) {
          throw new Error("Audio recording is empty");
        }
        
        if (audioBlob.size < 1000) {
          console.warn("Warning: Audio recording is very small, may be incomplete");
        }
        
        // For debugging, play the audio locally to verify it was recorded correctly
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        console.log("Loading audio for verification");
        
        // Wait for the audio to load before sending it
        await new Promise((resolve) => {
          audio.onloadedmetadata = () => {
            console.log(`Audio duration: ${audio.duration.toFixed(2)} seconds`);
            if (audio.duration < 0.5) {
              console.warn("Warning: Audio is very short, may not contain speech");
            }
            resolve();
          };
          audio.onerror = () => {
            console.error("Error loading audio for verification");
            resolve(); // Continue anyway
          };
          
          // Set a timeout in case the event never fires
          setTimeout(resolve, 1000);
        });
        
        // Play audio for verification (optional)
        try {
          console.log("Playing audio locally for verification");
          audio.volume = 0.3; // Lower volume for verification
          await audio.play();
          // Wait a moment to hear the start of the audio
          await new Promise(resolve => setTimeout(resolve, 300));
          audio.pause();
        } catch (playError) {
          console.warn("Could not play audio for verification:", playError);
        }
        
        // Create FormData to send to backend
        const formData = new FormData();
        
        // Use the detected mime type in the filename if possible
        let fileExtension = 'wav';
        if (audioBlob.type.includes('webm')) fileExtension = 'webm';
        else if (audioBlob.type.includes('mp4')) fileExtension = 'mp4';
        else if (audioBlob.type.includes('ogg')) fileExtension = 'ogg';
        
        formData.append('audio', audioBlob, `recording.${fileExtension}`);
        console.log(`Sending audio to server as recording.${fileExtension} (${audioBlob.type})`);
        
        // Add recording details to help with debugging
        formData.append('duration', audio.duration);
        formData.append('fileSize', audioBlob.size);
        formData.append('mimeType', audioBlob.type);
        formData.append('chunkCount', audioChunksRef.current.length);
        
        console.log("Sending audio to server for transcription...");
        
        // Send to backend for transcription and analysis with timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000); // 30-second timeout
        
        let response;
        try {
          response = await fetch('http://localhost:8000/transcribe', {
            method: 'POST',
            body: formData,
            signal: controller.signal
          });
          
          clearTimeout(timeoutId);
        } catch (fetchError) {
          clearTimeout(timeoutId);
          if (fetchError.name === 'AbortError') {
            throw new Error("Request timed out. The server is taking too long to respond.");
          }
          throw fetchError;
        }
        
        if (!response.ok) {
          const errorText = await response.text();
          console.error(`Server error (${response.status}):`, errorText);
          throw new Error(`Server responded with ${response.status}: ${errorText}`);
        }
        
        const data = await response.json();
        console.log("Server response:", data);
        
        if (data.error) {
          throw new Error(`Transcription error: ${data.error}`);
        }
        
        // Send the transcription and analysis back to parent component
        if (onTranscriptionReceived && data.transcript) {
          console.log(`Successfully transcribed: "${data.transcript}"`);
          onTranscriptionReceived(data.transcript, data.analysis);
        } else {
          throw new Error("No transcription in the response");
        }
      } catch (err) {
        console.error("Error processing audio:", err);
        
        // Provide more specific error messages to the user
        let userMessage = "Error processing audio. ";
        
        if (err.message.includes("No audio data")) {
          userMessage += "No audio was recorded. Please check your microphone and try again.";
        } else if (err.message.includes("Audio recording is empty")) {
          userMessage += "The recording was empty. Please speak clearly into your microphone.";
        } else if (err.message.includes("Could not understand audio")) {
          userMessage += "Could not understand the speech. Please speak clearly and try again.";
        } else if (err.message.includes("service")) {
          userMessage += "Speech recognition service unavailable. Please try again later.";
        } else if (err.message.includes("timed out")) {
          userMessage += "The request timed out. The server may be overloaded. Please try again.";
        } else if (err.message.includes("fetch")) {
          userMessage += "Network error. Please check your internet connection and try again.";
        } else {
          userMessage += "Please check your microphone connection and try again.";
        }
        
        // Log detailed error information for debugging
        console.error({
          errorType: err.name,
          errorMessage: err.message,
          errorStack: err.stack,
          audioInfo: {
            chunks: audioChunksRef.current?.length || 0,
            totalSize: audioChunksRef.current?.reduce((sum, chunk) => sum + chunk.size, 0) || 0
          }
        });
        
        alert(userMessage);
        
        // If parent provided a handler, send the error with more details
        if (onTranscriptionReceived) {
          onTranscriptionReceived(null, { 
            error: err.message,
            errorType: err.name,
            userMessage: userMessage
          });
        }
      } finally {
        // Clean up
        setIsProcessing(false);
        setIsRecording(false);
        setRecordingTime(0);
        setAudioLevel(0);
        
        // Stop all audio tracks
        if (mediaRecorderRef.current && mediaRecorderRef.current.stream) {
          mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
        }
      }
    };
    
    // Stop the recording
    mediaRecorderRef.current.stop();
  };

  const toggleRecording = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  // Button text based on current state
  const getButtonText = () => {
    if (isProcessing) return '🔄 Processing...';
    if (isRecording) return `⏹️ Stop Recording (${formatTime(recordingTime)})`;
    return '🎤 Record Answer';
  };

  // Button content with icon based on current state
  const getButtonContent = () => {
    if (isProcessing) return (<><i className="fas fa-sync fa-spin"></i></>);
    if (isRecording) return (<><i className="fas fa-stop"></i></>);
    return (<><i className="fas fa-microphone"></i></>);
  };

  return (
    <div className="voice-btn-container">
      <button
        className={`voice-btn ${isRecording ? 'recording' : ''}`}
        onClick={toggleRecording}
        disabled={disabled || isProcessing}
        title={isProcessing ? 'Processing...' : isRecording ? 'Stop Recording' : 'Record Answer'}
      >
        {getButtonContent()}
      </button>
      {isRecording && (
        <>
          <div className="audio-visualizer">
            <div 
              className="audio-level-bar" 
              style={{ width: `${Math.min(100, audioLevel / 2.55)}%` }}
            ></div>
          </div>
          <div className="recording-timer">
            {formatTime(recordingTime)}
          </div>
          <div className="recording-indicator">
            <div className="recording-indicator-dot"></div>
            Recording in progress
          </div>
        </>
      )}
    </div>
  );
};

export default VoiceButton;
