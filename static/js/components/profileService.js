import { api } from './api';

class ProfileService {
    async getProfile() {
        return await api.get('/profiles/');
    }

    async updateProfile(data) {
        return await api.put('/profiles/', data);
    }

    async getFullProfile() {
        return await api.get('/profiles/full_profile/');
    }

    async getProfileStats() {
        return await api.get('/profiles/stats/');
    }

    // Work Experience
    async getWorkExperiences() {
        return await api.get('/work-experiences/');
    }

    async addWorkExperience(data) {
        return await api.post('/work-experiences/', data);
    }

    async updateWorkExperience(id, data) {
        return await api.put(`/work-experiences/${id}/`, data);
    }

    async deleteWorkExperience(id) {
        return await api.delete(`/work-experiences/${id}/`);
    }

    async getCurrentPosition() {
        return await api.get('/work-experiences/current_position/');
    }

    async getWorkExperiencesByCompany(company) {
        return await api.get(`/work-experiences/by_company/?company=${company}`);
    }

    // Projects
    async getProjects() {
        return await api.get('/projects/');
    }

    async addProject(data) {
        return await api.post('/projects/', data);
    }

    async updateProject(id, data) {
        return await api.put(`/projects/${id}/`, data);
    }

    async deleteProject(id) {
        return await api.delete(`/projects/${id}/`);
    }

    async getProjectsByTechnology(technology) {
        return await api.get(`/projects/by_technology/?technology=${technology}`);
    }

    // Education
    async getEducation() {
        return await api.get('/education/');
    }

    async addEducation(data) {
        return await api.post('/education/', data);
    }

    async updateEducation(id, data) {
        return await api.put(`/education/${id}/`, data);
    }

    async deleteEducation(id) {
        return await api.delete(`/education/${id}/`);
    }

    async getEducationByInstitution(institution) {
        return await api.get(`/education/by_institution/?institution=${institution}`);
    }

    // Certifications
    async getCertifications() {
        return await api.get('/certifications/');
    }

    async addCertification(data) {
        return await api.post('/certifications/', data);
    }

    async updateCertification(id, data) {
        return await api.put(`/certifications/${id}/`, data);
    }

    async deleteCertification(id) {
        return await api.delete(`/certifications/${id}/`);
    }

    async getCertificationsByIssuer(issuer) {
        return await api.get(`/certifications/by_issuer/?issuer=${issuer}`);
    }

    // Publications
    async getPublications() {
        return await api.get('/publications/');
    }

    async addPublication(data) {
        return await api.post('/publications/', data);
    }

    async updatePublication(id, data) {
        return await api.put(`/publications/${id}/`, data);
    }

    async deletePublication(id) {
        return await api.delete(`/publications/${id}/`);
    }

    async getPublicationsByPublisher(publisher) {
        return await api.get(`/publications/by_publisher/?publisher=${publisher}`);
    }

    // Skills
    async getSkills() {
        return await api.get('/skills/');
    }

    async addSkill(data) {
        return await api.post('/skills/', data);
    }

    async updateSkill(id, data) {
        return await api.put(`/skills/${id}/`, data);
    }

    async deleteSkill(id) {
        return await api.delete(`/skills/${id}/`);
    }

    async getSkillsByCategory(category) {
        return await api.get(`/skills/by_category/?category=${category}`);
    }

    async getSkillsByProficiency(proficiency) {
        return await api.get(`/skills/by_proficiency/?proficiency=${proficiency}`);
    }
}

export const profileService = new ProfileService(); 