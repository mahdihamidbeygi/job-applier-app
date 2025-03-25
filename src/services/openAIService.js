import { ChatOpenAI } from '@langchain/openai';
import { HumanMessage } from '@langchain/core/messages';

export class OpenAIService {
  constructor() {
    this.llm = new ChatOpenAI({
      modelName: 'gpt-4',
      temperature: 0.2,
    });
  }

  async invoke(messages) {
    return await this.llm.invoke(messages);
  }

  async call(prompt) {
    return await this.llm.invoke([new HumanMessage(prompt)]);
  }
} 