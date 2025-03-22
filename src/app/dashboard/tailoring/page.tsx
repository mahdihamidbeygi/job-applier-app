"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

export default function TailoringDocumentsPage() {
  const [jobDescription, setJobDescription] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [resumeUrl, setResumeUrl] = useState<string | null>(null);
  const [coverLetterUrl, setCoverLetterUrl] = useState<string | null>(null);

  const handleGenerateDocuments = async () => {
    if (!jobDescription.trim()) {
      return;
    }

    setIsLoading(true);
    setResumeUrl(null);
    setCoverLetterUrl(null);
    
    try {
      // Generate resume
      const resumeResponse = await fetch("/api/tailoring/resume", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jobDescription }),
      });
      
      if (!resumeResponse.ok) {
        throw new Error("Failed to generate tailored resume");
      }
      
      const resumeBlob = await resumeResponse.blob();
      setResumeUrl(URL.createObjectURL(resumeBlob));
      
      // Generate cover letter
      const coverLetterResponse = await fetch("/api/tailoring/cover-letter", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jobDescription }),
      });
      
      if (!coverLetterResponse.ok) {
        throw new Error("Failed to generate tailored cover letter");
      }
      
      const coverLetterBlob = await coverLetterResponse.blob();
      setCoverLetterUrl(URL.createObjectURL(coverLetterBlob));
    } catch (error) {
      console.error("Error generating tailored documents:", error);
      alert("Failed to generate tailored documents. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container mx-auto py-8">
      <h1 className="text-3xl font-bold mb-4">Tailor Your Documents</h1>
      <p className="text-gray-600 mb-6">
        Paste a job description below to generate tailored resume and cover letter documents
        that highlight your relevant skills and experience for this specific position.
      </p>
      
      <Card className="p-6">
        <div className="mb-4">
          <label 
            htmlFor="jobDescription" 
            className="block text-sm font-medium text-gray-700 mb-2"
          >
            Job Description
          </label>
          <textarea
            id="jobDescription"
            className="w-full h-64 p-4 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Paste the job description here..."
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
          />
        </div>
        
        <Button 
          onClick={handleGenerateDocuments} 
          disabled={!jobDescription.trim() || isLoading}
          className="w-full"
        >
          {isLoading ? "Generating Documents..." : "Generate Tailored Documents"}
        </Button>
      </Card>
      
      <Separator className="my-8" />
      
      <div className="grid md:grid-cols-2 gap-6">
        <div>
          <h2 className="text-xl font-bold mb-2">Resume</h2>
          <p className="text-gray-600 mb-4">
            Your tailored resume will highlight skills and experiences most relevant to this job position.
          </p>
          <Button 
            onClick={() => resumeUrl && window.open(resumeUrl, "_blank")}
            disabled={!resumeUrl}
            variant="outline"
            className="w-full"
          >
            Download Resume
          </Button>
        </div>
        
        <div>
          <h2 className="text-xl font-bold mb-2">Cover Letter</h2>
          <p className="text-gray-600 mb-4">
            Your personalized cover letter will explain why you&apos;re a perfect fit for this role
            based on the job requirements.
          </p>
          <Button 
            onClick={() => coverLetterUrl && window.open(coverLetterUrl, "_blank")}
            disabled={!coverLetterUrl}
            variant="outline"
            className="w-full"
          >
            Download Cover Letter
          </Button>
        </div>
      </div>
    </div>
  );
} 