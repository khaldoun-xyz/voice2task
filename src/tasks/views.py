# views.py
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import spacy
from .models import Task

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    import subprocess
    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load("en_core_web_sm")

def home(request):
    return render(request, 'home.html')

@csrf_exempt
def process_voice(request):
    if request.method == "POST":
        voice_text = request.POST.get("voice_text", "")
        
        if not voice_text:
            return JsonResponse({"status": "error", "error": "No voice text provided"}, status=400)
        
        try:
            doc = nlp(voice_text)
            
            action = next((token.text for token in doc if token.pos_ == "VERB"), "Task")
            
            recipient = None
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    recipient = ent.text
                    break
            

            if not recipient:
                group_keywords = ["team", "department", "group", "committee"]
                for token in doc:
                    if token.text.lower() in group_keywords and token.dep_ == "dobj":
                        recipient = "the " + token.text.lower()
                        break
            

            if not recipient:
                for token in doc:
                    if token.dep_ == "dobj" and token.pos_ == "NOUN":
                        recipient = token.text
                        break
            

            topic = ""
            if "about" in voice_text.lower():
                about_index = voice_text.lower().index("about")
                deadline_keyword = "by" if "by" in voice_text.lower() else None
                if deadline_keyword:
                    deadline_index = voice_text.lower().index(deadline_keyword)
                    topic = voice_text[about_index+6:deadline_index].strip()
                else:
                    topic = voice_text[about_index+6:].strip()
            

            deadline = None
            for ent in doc.ents:
                if ent.label_ == "DATE":
                    deadline = ent.text
                    break
            
            if not deadline and "by" in voice_text.lower():
                deadline_part = voice_text.lower().split("by")[-1].strip()
                deadline_doc = nlp(deadline_part)
                deadline = next((ent.text for ent in deadline_doc.ents if ent.label_ == "DATE"), deadline_part)
            

            feedback_message = f"Task created: {action}"
            if recipient:
                feedback_message += f" {recipient}"
            if topic:
                feedback_message += f" about {topic}"
            if deadline:
                feedback_message += f" - Due {deadline}"

            task = Task.objects.create(
                user="web_user",
                voice_input=voice_text,
                action=action,
                person=recipient or "",  
                topic=topic or "",
                deadline=deadline or ""
            )
            
            return JsonResponse({
                "status": "success",
                "data": {
                    "action": action,
                    "person": recipient,  
                    "topic": topic,
                    "deadline": deadline,
                    "feedback": feedback_message 
                }
            })
            
        except Exception as e:
            return JsonResponse({
                "status": "error",
                "error": f"Error processing voice command: {str(e)}"
            }, status=500)