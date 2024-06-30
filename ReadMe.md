Read me please :)

Introduction to the Project:

Hello! I'm not going to extend myself too much on this ReadMe. My name is Mark and I'm the developer for this interface that bridges text-to-speech and speech-to-text with an AI assistant. This small project's goal is to make a small and easy to use interface to bridge open source solutions available, for me to be able to have my own AI assistant and for me to learn Python. As this turned out to be a more fun project than what I originally thought so I asked: Why keep it all for myself when I could share it with other people and help them see some ways to perform this goal I had? 

This one of the reasons as for why this project has a GitHub. The other reasons would be for BackUp Purposes, being able to be able to view my progress through this project, to track any bugs I find during any testing and to get feedback on the project and Ideas on how to improve it should you like it!

Lastly, I do want to reference that this project may be viewed similar to some sort of a Neuro-Sama clone or other AI Vtuber clone (I'm not aware of many at the time of writting this).  While that is not the objective of the project, I do want to leave here some praise to Vedal and other Developers that have created similar Programs/Interfaces/Projects to this one. Part of the reason I've created this was due to a dream I had as a kid to create or have my own computer assistant and the other was from seeing people on the internet, such as Vedal with Neuro-Sama, being able to create them.



Important Disclaimer:

As mentioned above, this projet is mostly me making an interface to bridge open source solutions available. Given this I do want to leave it clear here that I do not own any right to the modules, libraries and solutions I used for the Project. Below is a list of all of these same modules, libraries and solutions that I'm using for this project. Do note that this may be updated based on project updates and that I may be missing one or two here as I have plenty of python Libraries already installed on my computer which, although I believe I'm not using them, it may be used in the project without me realizing:

Coding Language and version:
  Python 3.10 (64-bit)

Python Modules/Libraries:
  tkinter
  speech_recognition
  threading
  ollama
  edge_tts
  asyncio
  os
  multiprocessing
  sounddevice as sd
  soundfile as sf
  time
  uuid
  
Open Source Software Used in the code:
  Ollama (For the AI chat feature) - https://ollama.com/

Additional Software that I'm using (While it's not used in the code or required to run it, I do want to reference them as I personally used them and confirmed they work with the project without any major issues)
  Realtime Voice Changer Client (Using this for changing the Voices) - https://github.com/w-okada/voice-changer
  Vtube Studio (For a visual model which you can associate your assitance with) - Available in Steam: "https://store.steampowered.com/app/1325860/VTube_Studio/". I'll also leave it their official website here: "https://denchisoft.com/"
  Virtual Audio Cable (Using this to allow me to channel the output of the AI's voice to the Voice Changing Software without hearing the Edge TTS voice) - You can get it here: https://vb-audio.com/Cable/



Additional Disclaimer:

The creator of this interface cannot be held liable for any misuse, improper application, or any consequences arising from the use of this interface. Users are solely responsible for how they utilize the interface for the AI assistant and must ensure that their usage complies with all applicable laws and regulations. By using this interface, you agree to indemnify and hold harmless the creator from any claims, damages, or legal actions resulting from your use of this application.


Requirements:

While I can't give an exact list of requirements for this project, here's what I'll recommend for those who want to at least have a baseline for trying this project:
  CPU - I'm unsure how powerfull the CPU needs to be as I use CUDA for the AI processing power, but if you do not have a good graphics card and will be using CPU processing, please make sure to have a good CPU (Preferrably a high end chip from recent generations) and please be aware that CPU generation tends to be slower than GPU generations based on my current understanding of the generation process.
  RAM - 16 GB of RAM should be around the minimum to run the program but I would recommend having 32GB if you are considering being able to play games which use quite a bit of RAM with the program.
  GPU - I'd recommend a NVidia GPU with at least 12GB of VRAM like a 4070 (which is what I have). I believe it is possible to use a 8GB VRAM GPU if you use a smaller LLM, but for running llama3 you will need around 8.3 GB of VRAM (Based on what I see in task manager at the time of writting this, however if you search online it says the llama3 requires 16GB). In regards to other GPU manufacturers such as AMD and Intel, I'm unable to confirm if they are currently compatible with the program. I believe AMD users may be able to use it based on this post on ollama's blog https://ollama.com/blog/amd-preview, but I'm unable to test it on this end.)

My Specs (If you want to have a reference of what I use):
CPU - Ryzen 5900X
RAM - 32GB
GPU - NVidia Geforce RTX 4070

Project Goals:

My main goal is to create an easy to use AI assistant. Something that just works out of the gate and doesn't need to be finessed to work for an end user. 
My other goal is to learn Python. While this isn't my first time using Python, I've never actually made a project with it as I've always made projects with Visual Basic as that was the language I've learned. This means that while initially the project may not be the most robust or complete in terms of quality of life features, I'll do my best to ensure that the project works as best as possible and will make improvements wherever it may be deemed needed.



Currently Implemented Features:

  Speech-to-Text with Ambient Noise filtration - Simple Microphone Voice Recognition. It's not perfect as it sometimes cuts a sentence in half and sends both halfs at the same time, but I'm reviewing ways to improve it. The good news is that it currently works most of the time correctly. It uses the first two seconds after you click to turn on the mic to filter the ambient noise and, afterwards, you can talk into the microphone.
  AI Conversational User Interface - With this, I'm referring to the bridge between the Python Interface and Ollama which allows a conversation to occur.
  AI Conversational Chat Log - A simple chatlog to see the conversation if you don't want or cannot hear it. You can also see if a response has failed to be generated on it.
  Text-to-Speech - Currently uses Edge's TTS readers. This means that the program currently requires internet for TTS. Selected Edge as they have clear voices for reading, but they do lack the emotion when reading the answers. This is also being reviewed in order to be improved.
  Text-to-Speech Voice Selection - Selection of Edge's TTS readers with the option to select a Default.
  Context Editor - Used on the prompt sent to the AI. I will advise you to ensure the context is as simple as possible to ensure the AI stay's on the role you ask it to perform. I also advise to mention this at the end of your prompt: "Please focus on answering the following question taking the before mentioned role into consideration, within a maximum of 100 words and do not mention any actions/sentiments you may have or act:". This will help the AI be concise with their answers, but feel free to adapt this ending based on your needs/preferences.
  Audio Output Selection - A simple menu to choose the TTS's output channel. Used for both choosing your preferred audio device to listen to the AI or if you want to use a Virtual Cable to redirect the output to a voice changer.
  Light/Dark Mode - Do you hate getting blinded at night? So do I! Dark mode is here to help you! All you need to do is click on the letter D near the Microphone and it will change the mode hahaha :)
  AI Conversational Memory - I'm not going to fully explain here how it works, but basically the AI is able to remember an amount of messages that you send even if you close the program. This number is fully alterable by you. At the time of writting this the base number is 3 as it helps with hallucinations, but I've tested with a 30 messages memory and it didn't have any major hallucination as far as I could tell. This is still being actively worked upon as it does involve "prompt engineering" for the memory, but just be aware that it will only remember the most recent messages for the limit you've set up. For 3 messages, your 4th message would replace your first message, your 5th would replace your 2nd message, your 6th the 3rd message and so on.



Current Work-In-Progress/Being Reviewed Features:

  Better Speech-to-text - While the current one works as mentioned above, I do want to make it more reliable. As such I'm actively reviewing this aspect of the project.
  Better Text-to-speech - While offline TTS is the current priority to help improve the Project's independence, I do plan on trying to figure on how make the TTS have more emotion while reading the answers.
  Better Vtube Studio Compatibility - As mentioned on my Disclaimer, I do use this Project with VTube Studio. This means that I have two easy options for now. 1 - "Have a still avatar that only moves the mouth when speaking" or 2 - "Have a permanently 'bobbing' avatar that moves the mouth when speaking". I want to review how to improve this and/or how to create a method for inputs to be sent directly to Vtube Studio
  Settings Menu - Making Configurations be in one single menu instead of having their own dedicated menu.
  Better AI Memory - Prompt Engineering to make the AI remember the previous messages, but not focus on them.
  AI Model Choise - Being able to select an installed ollama AI (LLM) of your preference.
  Memory Clear - Just an easy way to erase all previous message logs to wipe the AI's memory.




Current Idea section (Possible Future Features):

  Custom Themes
  Background Images
  Music Generation
  Built-in Games for the user to play with or against the AI
  Document Analysis
  Programmable Dictionary for Specific Actions for Prompts (Ex: Saying "Please review document X" on the question would trigger a specific function of the AI.)
  Vision (As in being able to view the user's screen and reacting to it)



Ending to the document:

If you've read all of the above, Thank you! It means a lot to me that you took the time to read it.
