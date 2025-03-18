# LinkedIn Profile Parsing

This directory contains implementations for parsing LinkedIn profile data using different approaches.

## Files

- `profileEnricher.ts` - Main module for enriching user profiles with data from social media platforms (GitHub and LinkedIn)
- `linkedinParser.ts` - Implementation using the Proxycurl API for LinkedIn profile data extraction
- `linkedinParserLangChain.ts` - Implementation using LangChain and OpenAI for LinkedIn profile data extraction

## LinkedIn Profile Parsing Approaches

### 1. Proxycurl API (linkedinParser.ts)

This implementation uses the Proxycurl API to fetch LinkedIn profile data in a compliant way. Proxycurl is a commercial service that provides LinkedIn profile data through an API, respecting LinkedIn's terms of service.

To use this implementation:
- Add `PROXYCURL_API_KEY` to your environment variables
- The implementation will fall back to mock data generation if the API key is not available

### 2. LangChain + OpenAI (linkedinParserLangChain.ts)

This implementation uses LangChain and OpenAI to parse LinkedIn profile HTML content. In a real-world scenario, you would need to:
1. Use a headless browser like Puppeteer to fetch the HTML content of a LinkedIn profile page
2. Pass the HTML content to the LangChain parser
3. The parser uses OpenAI to extract structured information from the HTML

To use this implementation:
- Add `OPENAI_API_KEY` to your environment variables
- The current implementation uses mock HTML content for demonstration purposes

## Integration

The `profileEnricher.ts` module integrates both approaches:
1. It first tries to use the LangChain-based parser directly with the LinkedIn URL
2. If that fails, it falls back to the username-based approach, which:
   - First tries to use the LangChain-based parser with the constructed URL
   - If that fails, it falls back to mock data generation

## Type Definitions

The `LinkedInProfile` interface is defined in both `profileEnricher.ts` and `linkedinParserLangChain.ts`. The latter exports the type for use in other files.

## Future Improvements

1. Implement proper HTML fetching using Puppeteer or similar tools
2. Add caching to reduce API calls and improve performance
3. Implement error handling and rate limiting
4. Add support for more social media platforms
5. Improve the prompt for the LangChain-based parser to extract more accurate information 