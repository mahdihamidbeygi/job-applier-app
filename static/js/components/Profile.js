import React, { useState, useEffect } from 'react';
import { profileService } from './profileService';

const Profile = () => {
    const [profile, setProfile] = useState(null);
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [activeSection, setActiveSection] = useState('overview');

    useEffect(() => {
        loadProfile();
    }, []);

    const loadProfile = async () => {
        try {
            setLoading(true);
            const [profileData, statsData] = await Promise.all([
                profileService.getFullProfile(),
                profileService.getProfileStats()
            ]);
            setProfile(profileData);
            setStats(statsData);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    if (loading) return (
        <div className="loading-container">
            <div className="loading-spinner"></div>
            <p>Loading your profile...</p>
        </div>
    );

    if (error) return (
        <div className="error-container">
            <h2>Error Loading Profile</h2>
            <p>{error}</p>
            <button onClick={loadProfile} className="retry-button">Try Again</button>
        </div>
    );

    if (!profile) return (
        <div className="no-profile-container">
            <h2>No Profile Found</h2>
            <p>Please create your profile to get started.</p>
        </div>
    );

    const renderOverview = () => (
        <>
            <div className="profile-header">
                <h1>{profile.headline}</h1>
                <p>{profile.professional_summary}</p>
            </div>

            <div className="profile-stats">
                <h2>Profile Statistics</h2>
                <div className="stats-grid">
                    <div className="stat-item">
                        <h3>Work Experience</h3>
                        <p>{stats.total_experience}</p>
                    </div>
                    <div className="stat-item">
                        <h3>Projects</h3>
                        <p>{stats.total_projects}</p>
                    </div>
                    <div className="stat-item">
                        <h3>Skills</h3>
                        <p>{stats.total_skills}</p>
                    </div>
                    <div className="stat-item">
                        <h3>Certifications</h3>
                        <p>{stats.total_certifications}</p>
                    </div>
                    <div className="stat-item">
                        <h3>Publications</h3>
                        <p>{stats.total_publications}</p>
                    </div>
                </div>
            </div>
        </>
    );

    const renderWorkExperience = () => (
        <section className="work-experience">
            <h2>Work Experience</h2>
            {profile.work_experiences.map(exp => (
                <div key={exp.id} className="experience-item">
                    <h3>{exp.position} at {exp.company}</h3>
                    <p className="date-range">
                        {exp.start_date} - {exp.current ? 'Present' : exp.end_date}
                    </p>
                    <p className="location">{exp.location}</p>
                    <p className="description">{exp.description}</p>
                    <p className="technologies">Technologies: {exp.technologies}</p>
                </div>
            ))}
        </section>
    );

    const renderProjects = () => (
        <section className="projects">
            <h2>Projects</h2>
            {profile.projects.map(project => (
                <div key={project.id} className="project-item">
                    <h3>{project.title}</h3>
                    <p className="date-range">
                        {project.start_date} - {project.end_date}
                    </p>
                    <p className="description">{project.description}</p>
                    <p className="technologies">Technologies: {project.technologies}</p>
                    <div className="project-links">
                        {project.github_url && (
                            <a href={project.github_url} target="_blank" rel="noopener noreferrer">
                                <span>GitHub</span>
                            </a>
                        )}
                        {project.live_url && (
                            <a href={project.live_url} target="_blank" rel="noopener noreferrer">
                                <span>Live Demo</span>
                            </a>
                        )}
                    </div>
                </div>
            ))}
        </section>
    );

    const renderEducation = () => (
        <section className="education">
            <h2>Education</h2>
            {profile.education.map(edu => (
                <div key={edu.id} className="education-item">
                    <h3>{edu.institution}</h3>
                    <p className="degree">{edu.degree} in {edu.field_of_study}</p>
                    <p className="date-range">
                        {edu.start_date} - {edu.current ? 'Present' : edu.end_date}
                    </p>
                    {edu.gpa && <p className="gpa">GPA: {edu.gpa}</p>}
                    <p className="achievements">{edu.achievements}</p>
                </div>
            ))}
        </section>
    );

    const renderCertifications = () => (
        <section className="certifications">
            <h2>Certifications</h2>
            {profile.certifications.map(cert => (
                <div key={cert.id} className="certification-item">
                    <h3>{cert.name}</h3>
                    <p>Issuer: {cert.issuer}</p>
                    <p className="date-range">
                        Issued: {cert.issue_date}
                        {cert.expiry_date && ` - Expires: ${cert.expiry_date}`}
                    </p>
                    {cert.credential_id && <p>Credential ID: {cert.credential_id}</p>}
                    {cert.credential_url && (
                        <a href={cert.credential_url} target="_blank" rel="noopener noreferrer">
                            View Credential
                        </a>
                    )}
                </div>
            ))}
        </section>
    );

    const renderPublications = () => (
        <section className="publications">
            <h2>Publications</h2>
            {profile.publications.map(pub => (
                <div key={pub.id} className="publication-item">
                    <h3>{pub.title}</h3>
                    <p>Authors: {pub.authors}</p>
                    <p>Published: {pub.publication_date}</p>
                    <p>Publisher: {pub.publisher}</p>
                    <p>Journal: {pub.journal}</p>
                    {pub.doi && <p>DOI: {pub.doi}</p>}
                    <p className="abstract">{pub.abstract}</p>
                    {pub.url && (
                        <a href={pub.url} target="_blank" rel="noopener noreferrer">
                            View Publication
                        </a>
                    )}
                </div>
            ))}
        </section>
    );

    const renderSkills = () => (
        <section className="skills">
            <h2>Skills</h2>
            <div className="skills-grid">
                {profile.skills.map(skill => (
                    <div key={skill.id} className="skill-item">
                        <h3>{skill.name}</h3>
                        <p>Category: {skill.category}</p>
                        <p>Proficiency: {skill.proficiency}</p>
                    </div>
                ))}
            </div>
        </section>
    );

    return (
        <div className="profile-container">
            <nav className="profile-nav">
                <button 
                    className={`nav-item ${activeSection === 'overview' ? 'active' : ''}`}
                    onClick={() => setActiveSection('overview')}
                >
                    Overview
                </button>
                <button 
                    className={`nav-item ${activeSection === 'experience' ? 'active' : ''}`}
                    onClick={() => setActiveSection('experience')}
                >
                    Experience
                </button>
                <button 
                    className={`nav-item ${activeSection === 'projects' ? 'active' : ''}`}
                    onClick={() => setActiveSection('projects')}
                >
                    Projects
                </button>
                <button 
                    className={`nav-item ${activeSection === 'education' ? 'active' : ''}`}
                    onClick={() => setActiveSection('education')}
                >
                    Education
                </button>
                <button 
                    className={`nav-item ${activeSection === 'certifications' ? 'active' : ''}`}
                    onClick={() => setActiveSection('certifications')}
                >
                    Certifications
                </button>
                <button 
                    className={`nav-item ${activeSection === 'publications' ? 'active' : ''}`}
                    onClick={() => setActiveSection('publications')}
                >
                    Publications
                </button>
                <button 
                    className={`nav-item ${activeSection === 'skills' ? 'active' : ''}`}
                    onClick={() => setActiveSection('skills')}
                >
                    Skills
                </button>
            </nav>

            <div className="profile-content">
                {activeSection === 'overview' && renderOverview()}
                {activeSection === 'experience' && renderWorkExperience()}
                {activeSection === 'projects' && renderProjects()}
                {activeSection === 'education' && renderEducation()}
                {activeSection === 'certifications' && renderCertifications()}
                {activeSection === 'publications' && renderPublications()}
                {activeSection === 'skills' && renderSkills()}
            </div>
        </div>
    );
};

export default Profile; 