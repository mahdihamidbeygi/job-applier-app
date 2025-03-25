'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Loader2 } from 'lucide-react';
import { toast } from 'react-hot-toast';

export default function JobSkillsAnalysis({ jobId, jobTitle, companyName }) {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisData, setAnalysisData] = useState(null);
  const [isGeneratingResume, setIsGeneratingResume] = useState(false);
  const [isGeneratingCoverLetter, setIsGeneratingCoverLetter] = useState(false);

  const analyzeJob = async () => {
    try {
      setIsAnalyzing(true);
      const response = await fetch(`/api/jobs/${jobId}/analyze`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Failed to analyze job');
      }

      const data = await response.json();
      setAnalysisData(data.data);
      toast.success('Job analysis completed successfully');
    } catch (error) {
      console.error('Error analyzing job:', error);
      toast.error('Failed to analyze job');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const generateResume = async () => {
    try {
      setIsGeneratingResume(true);
      const response = await fetch(`/api/download/resume/${jobId}`, {
        method: 'GET',
      });

      if (!response.ok) {
        throw new Error('Failed to generate resume');
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${companyName}_${jobTitle}_Resume.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success('Resume generated successfully');
    } catch (error) {
      console.error('Error generating resume:', error);
      toast.error('Failed to generate resume');
    } finally {
      setIsGeneratingResume(false);
    }
  };

  const generateCoverLetter = async () => {
    try {
      setIsGeneratingCoverLetter(true);
      const response = await fetch(`/api/download/cover-letter/${jobId}`, {
        method: 'GET',
      });

      if (!response.ok) {
        throw new Error('Failed to generate cover letter');
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${companyName}_${jobTitle}_CoverLetter.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success('Cover letter generated successfully');
    } catch (error) {
      console.error('Error generating cover letter:', error);
      toast.error('Failed to generate cover letter');
    } finally {
      setIsGeneratingCoverLetter(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-100">Skills Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          {!analysisData ? (
            <div className="space-y-4">
              <p className="text-slate-300">
                Analyze the job requirements and match them with your skills to get personalized recommendations.
              </p>
              <Button
                onClick={analyzeJob}
                disabled={isAnalyzing}
                className="bg-blue-600 hover:bg-blue-700 text-white"
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  'Analyze Job Requirements'
                )}
              </Button>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Skills Match Score */}
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <h3 className="text-lg font-semibold text-slate-100">Skills Match Score</h3>
                  <span className="text-2xl font-bold text-blue-400">
                    {analysisData.skillsMatch.matchScore}%
                  </span>
                </div>
                <Progress value={analysisData.skillsMatch.matchScore} className="h-2" />
              </div>

              {/* Matching Skills */}
              <div className="space-y-2">
                <h3 className="text-lg font-semibold text-slate-100">Matching Skills</h3>
                <div className="flex flex-wrap gap-2">
                  {analysisData.skillsMatch.matchingSkills.map((skill, index) => (
                    <span
                      key={index}
                      className="px-3 py-1 bg-green-900 text-green-100 rounded-full text-sm"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>

              {/* Missing Skills */}
              <div className="space-y-2">
                <h3 className="text-lg font-semibold text-slate-100">Missing Skills</h3>
                <div className="flex flex-wrap gap-2">
                  {analysisData.skillsMatch.missingSkills.map((skill, index) => (
                    <span
                      key={index}
                      className="px-3 py-1 bg-red-900 text-red-100 rounded-full text-sm"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>

              {/* Recommendations */}
              <div className="space-y-2">
                <h3 className="text-lg font-semibold text-slate-100">Recommendations</h3>
                <ul className="list-disc list-inside space-y-1 text-slate-300">
                  {analysisData.skillsMatch.recommendations.map((rec, index) => (
                    <li key={index}>{rec}</li>
                  ))}
                </ul>
              </div>

              {/* Document Generation */}
              <div className="space-y-4 pt-4">
                <h3 className="text-lg font-semibold text-slate-100">Generate Documents</h3>
                <div className="flex gap-4">
                  <Button
                    onClick={generateResume}
                    disabled={isGeneratingResume}
                    className="bg-blue-600 hover:bg-blue-700 text-white"
                  >
                    {isGeneratingResume ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Generating Resume...
                      </>
                    ) : (
                      'Generate Tailored Resume'
                    )}
                  </Button>
                  <Button
                    onClick={generateCoverLetter}
                    disabled={isGeneratingCoverLetter}
                    className="bg-blue-600 hover:bg-blue-700 text-white"
                  >
                    {isGeneratingCoverLetter ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Generating Cover Letter...
                      </>
                    ) : (
                      'Generate Cover Letter'
                    )}
                  </Button>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
} 