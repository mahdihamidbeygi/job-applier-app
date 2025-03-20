import { convertMarkdownToPDF } from './pdfConverter';
import fs from 'fs';
import path from 'path';

async function testPDFGeneration() {
  // Sample resume data
  const sampleData = {
    fullName: "John Doe",
    title: "Software Engineer",
    email: "john.doe@email.com",
    phone: "123-456-7890",
    location: "San Francisco, CA",
    linkedin: "linkedin.com/in/johndoe",
    github: "github.com/johndoe",
    summary: "Experienced software engineer with expertise in full-stack development and cloud architecture.",
    skills: {
      technical: [
        "JavaScript",
        "TypeScript",
        "React",
        "Node.js",
        "Python",
        "AWS",
        "Docker",
        "Kubernetes",
        "GraphQL",
        "MongoDB",
        "PostgreSQL",
        "Redis"
      ],
      soft: [
        "Team Leadership",
        "Problem Solving",
        "Communication",
        "Project Management"
      ]
    },
    experience: [
      {
        title: "Senior Software Engineer",
        company: "Tech Corp",
        location: "San Francisco, CA",
        startDate: "2020-01",
        endDate: "2023-12",
        achievements: [
          "Led development of microservices architecture serving 1M+ users",
          "Improved system performance by 40% through optimization",
          "Mentored junior developers and conducted code reviews"
        ]
      },
      {
        title: "Software Engineer",
        company: "Startup Inc",
        location: "San Francisco, CA",
        startDate: "2018-06",
        endDate: "2019-12",
        achievements: [
          "Developed and launched company's flagship product",
          "Implemented CI/CD pipeline reducing deployment time by 50%"
        ]
      }
    ],
    education: [
      {
        degree: "Master of Science",
        major: "Computer Science",
        school: "Stanford University",
        location: "Stanford, CA",
        graduationYear: "2018",
        gpa: "3.9",
        courses: ["Machine Learning", "Distributed Systems"],
        honors: ["Magna Cum Laude"]
      }
    ],
    projects: [
      {
        name: "Cloud Migration Project",
        description: "Led migration of legacy systems to cloud infrastructure",
        technologies: ["AWS", "Docker", "Terraform"],
        results: "Reduced operational costs by 30% and improved scalability"
      }
    ],
    certifications: [
      {
        name: "AWS Solutions Architect",
        issuer: "Amazon Web Services",
        date: "2022-06"
      }
    ]
  };

  try {
    // Generate PDF
    const pdfBuffer = await convertMarkdownToPDF("", sampleData);

    // Create output directory if it doesn't exist
    const outputDir = path.join(process.cwd(), 'test-output');
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir);
    }

    // Save the PDF
    const outputPath = path.join(outputDir, 'test-resume.pdf');
    fs.writeFileSync(outputPath, pdfBuffer);
    console.log(`PDF generated successfully at: ${outputPath}`);
  } catch (error) {
    console.error('Error generating PDF:', error);
  }
}

// Run the test
testPDFGeneration().catch(console.error); 