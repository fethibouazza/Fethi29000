import customtkinter as ctk
from tkinter import messagebox
import os
from google import genai
from google.genai import types
from google.genai.errors import APIError
from tkinter import TclError, END
import re
import threading

# مكتبة PDF: ReportLab
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_RIGHT

# 💡 إعداد الخطوط لـ ReportLab (لأقصى توافق على الهاتف)
print("INFO: Using built-in standard PDF fonts (Times-Roman, Helvetica).")

NORMAL_FONT_NAME = 'Times-Roman'
BOLD_FONT_NAME = 'Times-Bold'

# 💡 قائمة المجالات الموسعة (Genres)
ALL_GENRES = [
    "Technical Guide/Programming", "Educational Textbook (Academic)", "Historical Non-Fiction",
    "Self-Help/Motivational", "Personal Finance/Investment", "Fitness/Nutrition Guide",
    "Cookbook (Gourmet)", "Science Fiction (Hard Sci-Fi)", "Epic Fantasy Novel",
    "Crime/Noir Thriller", "Mystery/Detective Story", "Romantic Comedy Novel",
    "Poetry Collection (Modern)", "Travelogue/Cultural Exploration", "Business Strategy/Management",
    "Philosophy/Ethics Treatise", "Political Analysis/Current Affairs", "Art History/Appreciation",
    "Children's Story Book", "Spiritual/Meditation Guide", "Biography/Memoir",
    "Psychology/Behavioral Science", "Military History", "DIY/Crafting Manual",
    "Environmental Science/Ecology"
]

# --- 2. CONFIGURATION ESTHÉTIQUE ---
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")
FONT_SIZE = 16
LINES_PER_PAGE = 35

# --- 3. LOGIQUE GÉNERATION وَ فُورْمَاتَاجْ (GENERATION AND FORMATTING LOGIC) ---

def get_trending_topics(client, genre, language):
    """يستخدم Gemini Flash لاقتراح مواضيع رائجة بناءً على المجال."""
    prompt = (
        f"As a market researcher and publishing expert, identify the **5 most trending, unique, and commercially viable book topics** "
        f"in the '{genre}' genre right now. These topics must be highly appealing and likely to be bestsellers. "
        f"Format the output as a simple numbered list, one topic per line, with no explanations or extra text. "
        f"Write the list strictly in {language}."
    )
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        topics = [line.strip() for line in response.text.split('\n') if line.strip() and not line.strip().startswith(('API', 'error'))]
        return topics[:5]
    except APIError as e:
        return f"API Error: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

def generate_marketing_content(client, book_title, book_content_summary, language, genre):
    """
    توليد الوصف الجذاب (Pitch)، والهاشتاجات، ووصف غلاف الكتاب.
    تم فصل الاستدعاءات لضمان موثوقية كل مخرج.
    """
    
    # 1. وصف الكتاب (Pitch) - التأكيد على الجاذبية والنبرة العاطفية
    pitch_prompt = (
        f"Act as a top-tier book marketing copywriter. Create a **highly engaging, captivating, and commercially irresistible book pitch (blurb)** for the back cover of a book titled: '{book_title}'. "
        f"The content is about: '{book_content_summary}'. "
        f"The genre is '{genre}'. The tone must be emotional and persuasive. The length must be between 100 and 150 words. "
        f"Format the output into 2-3 short, punchy paragraphs for easy reading. "
        f"Write the pitch strictly in {language}."
    )
    
    # 2. توليد الهاشتاجات (Hashtags) - التأكيد على الرواج
    hashtag_prompt = (
        f"Generate the **10 best, most trending, and popular social media hashtags** for a book titled '{book_title}' in the '{genre}' genre. "
        f"List them on separate lines, starting each line with '#', with no other text or numbering. "
        f"They should be highly relevant and appropriate for {language} speakers."
    )
    
    # 3. توليد وصف الغلاف (Cover Description) - التأكيد على الإبداع والدقة
    cover_prompt = (
        f"Generate a **single, highly detailed, and creative prompt (maximum 200 tokens)** for an AI image generator (like Midjourney or DALL-E) to create a stunning, bestseller **book cover** for a '{genre}' book titled: '{book_title}'. "
        f"The prompt must include the visual style, mood, key symbolic elements, and composition. Example style: 'minimalist design, cinematic lighting, epic, vibrant color palette'. "
        f"The output must be a single, continuous paragraph, suitable for direct input into an image generator. The language of the prompt must be English."
    )
    
    # تنفيذ الاستدعاءات بشكل متسلسل
    results = {}
    
    try:
        # Pitch
        response_pitch = client.models.generate_content(model="gemini-2.5-flash", contents=pitch_prompt)
        results["pitch"] = response_pitch.text.strip()
        
        # Hashtags
        response_hashtags = client.models.generate_content(model="gemini-2.5-flash", contents=hashtag_prompt)
        results["hashtags"] = response_hashtags.text.strip()
        
        # Cover
        response_cover = client.models.generate_content(model="gemini-2.5-flash", contents=cover_prompt)
        results["cover_desc"] = response_cover.text.strip()
        
        return results
        
    except APIError as e:
        # إذا فشل أحد الاستدعاءات، نرجع رسالة خطأ مع النتائج الجزئية
        return {
            "pitch": results.get("pitch", f"API Error in Pitch Generation: {e}"),
            "hashtags": results.get("hashtags", f"API Error in Hashtag Generation: {e}"),
            "cover_desc": results.get("cover_desc", f"API Error in Cover Generation: {e}")
        }
    except Exception as e:
        return f"An unexpected error occurred (Marketing): {e}"


def get_book_plan(client, prompt, language="French", genre="Technical Guide/Programming"):
    """
    خطوة 1: توليد العنوان وخطة الكتاب فقط.
    (تم الإبقاء عليها كما هي لضمان جودة الخطة)
    """
    style_language = language
    language_instruction = (
        f"Write the #output strictly in {language}. "
        f"The writing style and section titles (e.g., Chapter, Part, Section, Introduction, Conclusion) must conform to the conventions of a professional **{genre}**. "
        f"The output must include a comprehensive **Table of Contents** with Parts, Chapters, and at least one level of Sub-Sections for each chapter. "
        f"IMPORTANT: Ensure that if you use the term 'Part', it is followed by a main Chapter (e.g., Part I, then Chapter 1)."
    )

    plan_prompt = (
        f"Act as the world's most **highly acclaimed, creative, and unique** professional writer specializing in the '{genre}' genre. "
        f"Your output must be an **unparalleled masterpiece** of originality, quality, and insightful depth. "
        f"The writing style must perfectly suit the genre. "
        f"Create a **unique and inventive book title** (that has no parallel) and a detailed plan (summary, "
        f"and main sections/chapters with a brief description for each). **Determine the number of chapters yourself to ensure the book is HUGE, extremely complete, detailed, and utterly captivating, equivalent to 80+ printed pages**. "
        f"{language_instruction} "
        f"The content must be about: '{prompt}'. "
        f"IMPORTANT: The first line must **ONLY** be the book title. Do not add any extra text or quotation marks to the title."
    )
    
    # التكوين المتقدم لـ Gemini: تفعيل الإبداع فقط
    config = types.GenerateContentConfig(
        temperature=0.85       # رفع الإبداع للعنوان والخطة
    )

    try:
        response_plan = client.models.generate_content(model="gemini-2.5-pro", contents=plan_prompt, config=config)
        return response_plan.text
    except APIError as e:
        return f"API Error (Plan): {e}"
    except Exception as e:
        return f"An unexpected error occurred (Plan): {e}"

def stream_book_content(client, book_plan, language="French", genre="Technical Guide/Programming"):
    """
    خطوة 2: توليد المحتوى بشكل متدفق (Streaming) بناءً على الخطة.
    (تم الإبقاء عليها كما هي لضمان جودة محتوى الكتاب)
    """
    style_language = language

    system_instruction = (
        f"You are the world's most brilliant and creative book author specializing in the {genre} genre. "
        f"Your work must be a unique, unparalleled masterpiece. Write the content consistently in the style required for a **{genre}** (e.g., narrative for novels, factual for educational, etc.)."
    )

    content_prompt = (
        f"Based on the following plan for a '{genre}', write the full, **highly detailed, unique, and masterfully high-quality** content of the book. "
        f"The content must be extremely extensive, detailed, and elaborate (equivalent to 80+ printed pages - **DO NOT STOP WRITING UNTIL THE BOOK IS COMPLETELY FINISHED**). "
        f"Structure it exactly like a professional printed '{genre}'. Ensure the writing quality is the **absolute best** possible, demonstrating unparalleled creativity and depth. "
        f"The content must be 100% original and not copied. "
        f"IMPORTANT: Use **NO MARKDOWN SYMBOLS** (like ##, *, etc.). "
        f"Format main headings (e.g., CHAPTER, PART, SECTION, INTRODUCTION, CONCLUSION) clearly on a separate line. "
        f"Use natural, human-like language in {style_language}. \n\n"
        f"BOOK PLAN:\n{book_plan}"
    )
    
    # تكوين متقدم لـ Gemini: تفعيل الإبداع
    config = types.GenerateContentConfig(
        temperature=0.85
    )

    try:
        response_stream = client.models.generate_content_stream(
            model="gemini-2.5-pro",
            contents=content_prompt,
            config=config
        )
        return response_stream
    except APIError as e:
        return f"API Error (Content): {e}"
    except Exception as e:
        return f"An unexpected error occurred (Content): {e}"


# 💡 دالة مخصصة لرسم رأس وتذييل الصفحة
def my_on_each_page(canvas, doc, title):
    canvas.saveState()
    page_num = canvas.getPageNumber()
    
    if page_num > 1:
        display_page_num = page_num - 1
        canvas.setFont(NORMAL_FONT_NAME, 10)
        canvas.drawCentredString(doc.pagesize[0] / 2, 30, str(display_page_num))
            
    canvas.restoreState()


# --- 4. CLASSE DE L'APPLICATION CUSTOMTKINTER ---

class TopicSelector(ctk.CTkToplevel):
    # ... (تم الإبقاء على كلاس TopicSelector كما هو)
    def __init__(self, master, topics, prompt_entry_widget, progress_label_widget, genre):
        super().__init__(master)
        self.title(f"Trending Topics for {genre}")
        self.geometry("500x350")
        self.attributes('-topmost', True)
        self.grab_set()

        self.prompt_entry = prompt_entry_widget
        self.progress_label = progress_label_widget

        ctk.CTkLabel(self, text=f"Top 5 Trending Topics in '{genre}':", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)

        ctk.CTkLabel(self, text="Click a button to **copy the topic** and **paste it automatically** into the prompt field.").pack(pady=(0, 15))

        for i, topic in enumerate(topics):
            button = ctk.CTkButton(
                self,
                text=f"{i+1}. {topic}",
                command=lambda t=topic: self.copy_and_select(t),
                width=450,
                anchor="w"
            )
            button.pack(pady=5)

    def copy_and_select(self, topic):
        self.clipboard_clear()
        self.clipboard_append(topic)

        self.prompt_entry.delete(0, END)
        self.prompt_entry.insert(0, topic)

        self.progress_label.configure(text=f"Status: Topic copied ('{topic[:30]}...') and pasted. Ready to generate!", text_color="green")

        self.destroy()

class BookWriterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Gemini Masterpiece Creator 📝")
        self.geometry("1000x800") 

        self.api_key = ctk.StringVar()
        self.language_var = ctk.StringVar(value="Arabic")
        self.genre_var = ctk.StringVar(value=ALL_GENRES[0])
        self.author_name_var = ctk.StringVar(value="A. Professional Writer")
        self.book_content_summary = "" 

        self.client = None
        self.full_content = []
        self.current_page = 0
        self.book_title = "Untitled Book"
        self.stream_buffer = ""
        self.estimated_tokens = 80000
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # ------------------ FRAME 1: INPUTS & SETTINGS ------------------
        settings_frame = ctk.CTkFrame(self)
        settings_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        settings_frame.grid_columnconfigure((0, 3), weight=0)
        settings_frame.grid_columnconfigure(1, weight=1)

        # API Key
        ctk.CTkLabel(settings_frame, text="Gemini API Key:").grid(row=0, column=0, padx=(10, 5), pady=5, sticky="w")
        self.api_entry = ctk.CTkEntry(settings_frame, textvariable=self.api_key, show="*", width=350)
        self.api_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        paste_key_button = ctk.CTkButton(settings_frame, text="Paste Key", width=100, command=lambda: self.paste_from_clipboard(self.api_entry))
        paste_key_button.grid(row=0, column=2, padx=(5, 10), pady=5, sticky="e")
        
        self.after(100, lambda: self.api_entry.bind("<FocusOut>", self.initialize_client))

        # Book Topic
        ctk.CTkLabel(settings_frame, text="Book Topic/Prompt:").grid(row=1, column=0, padx=(10, 5), pady=5, sticky="w")
        self.prompt_entry = ctk.CTkEntry(settings_frame, placeholder_text="e.g., 'The secrets of Python programming'", width=350)
        self.prompt_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        prompt_action_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        prompt_action_frame.grid(row=1, column=2, padx=(5, 10), pady=5, sticky="e")
        prompt_action_frame.columnconfigure((0, 1), weight=1)
        
        # زر اللصق للبرومبت
        paste_prompt_button = ctk.CTkButton(prompt_action_frame, text="Paste Prompt", width=100, command=lambda: self.paste_from_clipboard(self.prompt_entry))
        paste_prompt_button.grid(row=0, column=0, padx=5, sticky="e")

        self.trend_button = ctk.CTkButton(prompt_action_frame, text="Find Topics", width=100, command=self.find_trending_topics)
        self.trend_button.grid(row=0, column=1, padx=5, sticky="e")


        # Language
        ctk.CTkLabel(settings_frame, text="Language:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.language_option = ctk.CTkOptionMenu(settings_frame, values=["Arabic", "English", "French"], variable=self.language_var)
        self.language_option.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # Book Genre
        ctk.CTkLabel(settings_frame, text="Book Genre:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.genre_option = ctk.CTkOptionMenu(
            settings_frame,
            values=ALL_GENRES,
            variable=self.genre_var
        )
        self.genre_option.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        # Author Name
        ctk.CTkLabel(settings_frame, text="Author Name:").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.author_entry = ctk.CTkEntry(
            settings_frame,
            textvariable=self.author_name_var,
            placeholder_text="Enter the author's name here",
            width=350
        )
        self.author_entry.grid(row=4, column=1, padx=5, pady=5, sticky="ew")
        paste_author_button = ctk.CTkButton(settings_frame, text="Paste Name", width=100, command=lambda: self.paste_from_clipboard(self.author_entry))
        paste_author_button.grid(row=4, column=2, padx=(5, 10), pady=5, sticky="e")


        # ------------------ FRAME 2: ACTION BUTTON & PROGRESS ------------------
        action_frame = ctk.CTkFrame(self)
        action_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        action_frame.grid_columnconfigure((0, 1), weight=1)

        self.generate_button = ctk.CTkButton(action_frame, text="Start Masterpiece Generation", command=self.start_generation_thread, state="disabled", fg_color="green")
        self.generate_button.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.save_txt_button = ctk.CTkButton(action_frame, text="Save as TXT 💾", command=self.save_book_txt, state="disabled", fg_color="gray")
        self.save_txt_button.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        # شريط التقدم لوضع محدد
        self.progress_bar = ctk.CTkProgressBar(action_frame, mode="determinate")
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 5), sticky="ew")

        self.progress_label = ctk.CTkLabel(action_frame, text="Status: Ready", text_color="yellow")
        self.progress_label.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        
        
        # ------------------ FRAME 3: MARKETING CONTENT ------------------
        marketing_frame = ctk.CTkFrame(self)
        marketing_frame.grid(row=2, column=0, padx=20, pady=(10, 10), sticky="ew")
        marketing_frame.grid_columnconfigure(0, weight=1)
        marketing_frame.grid_columnconfigure(1, weight=1)

        # Book Pitch
        pitch_header_frame = ctk.CTkFrame(marketing_frame, fg_color="transparent")
        pitch_header_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 0), sticky="ew")
        pitch_header_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(pitch_header_frame, text="✅ **Book Pitch (Back Cover Blurb)**:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w")
        self.copy_pitch_button = ctk.CTkButton(pitch_header_frame, text="Copy Pitch", width=80, command=lambda: self.copy_from_textbox(self.pitch_box))
        self.copy_pitch_button.grid(row=0, column=1, sticky="e")
        
        self.pitch_box = ctk.CTkTextbox(marketing_frame, height=100, wrap="word", font=ctk.CTkFont(size=14))
        self.pitch_box.grid(row=1, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="ew")
        self.pitch_box.insert("0.0", "Book pitch will appear here after generation...")
        self.pitch_box.configure(state="disabled")

        # Hashtags
        hashtag_header_frame = ctk.CTkFrame(marketing_frame, fg_color="transparent")
        hashtag_header_frame.grid(row=2, column=0, padx=(10, 5), pady=(0, 0), sticky="ew")
        hashtag_header_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(hashtag_header_frame, text="🔥 **Social Media Hashtags**:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w")
        self.copy_hashtags_button = ctk.CTkButton(hashtag_header_frame, text="Copy Tags", width=80, command=lambda: self.copy_from_textbox(self.hashtags_box))
        self.copy_hashtags_button.grid(row=0, column=1, sticky="e")
        
        self.hashtags_box = ctk.CTkTextbox(marketing_frame, height=80, wrap="word", font=ctk.CTkFont(size=14))
        self.hashtags_box.grid(row=3, column=0, padx=(10, 5), pady=(5, 10), sticky="nsew")
        self.hashtags_box.insert("0.0", "Hashtags will appear here.")
        self.hashtags_box.configure(state="disabled")

        # Cover Prompt
        cover_header_frame = ctk.CTkFrame(marketing_frame, fg_color="transparent")
        cover_header_frame.grid(row=2, column=1, padx=(5, 10), pady=(0, 0), sticky="ew")
        cover_header_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(cover_header_frame, text="🎨 **AI Cover Prompt (English)**:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w")
        self.copy_cover_button = ctk.CTkButton(cover_header_frame, text="Copy Prompt", width=80, command=lambda: self.copy_from_textbox(self.cover_desc_box))
        self.copy_cover_button.grid(row=0, column=1, sticky="e")
        
        self.cover_desc_box = ctk.CTkTextbox(marketing_frame, height=80, wrap="word", font=ctk.CTkFont(size=14))
        self.cover_desc_box.grid(row=3, column=1, padx=(5, 10), pady=(5, 10), sticky="nsew")
        self.cover_desc_box.insert("0.0", "AI Cover Prompt will appear here.")
        self.cover_desc_box.configure(state="disabled")


        # ------------------ FRAME 4: OUTPUT DISPLAY (WITH PAGINATION) ------------------
        output_frame = ctk.CTkFrame(self)
        output_frame.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="nsew")
        output_frame.grid_columnconfigure(0, weight=1)
        output_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(output_frame, text="Book Preview (Streaming/Page Turn):").grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")

        self.output_text = ctk.CTkTextbox(output_frame, wrap="word", height=400, font=ctk.CTkFont(size=FONT_SIZE))
        self.output_text.grid(row=1, column=0, padx=10, pady=(5, 5), sticky="nsew")

        self.output_text.tag_config('header',
                                     foreground="#000000",
                                     spacing3=10)

        pagination_frame = ctk.CTkFrame(output_frame, fg_color="transparent")
        pagination_frame.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        pagination_frame.grid_columnconfigure((0, 2), weight=1)

        self.prev_button = ctk.CTkButton(pagination_frame, text="< Previous Page", command=self.show_previous_page, state="disabled", width=150)
        self.prev_button.grid(row=0, column=0, padx=5, sticky="w")

        self.page_label = ctk.CTkLabel(pagination_frame, text="Page 0/0")
        self.page_label.grid(row=0, column=1, padx=5)

        self.next_button = ctk.CTkButton(pagination_frame, text="Next Page >", command=self.show_next_page, state="disabled", width=150)
        self.next_button.grid(row=0, column=2, padx=5, sticky="e")

    # ------------------ PAGINATION LOGIC ------------------

    def paginate_content(self, content):
        lines = content.split('\n')
        self.full_content = []
        current_page_lines = []

        for line in lines:
            current_page_lines.append(line)
            if len(current_page_lines) >= LINES_PER_PAGE:
                self.full_content.append('\n'.join(current_page_lines))
                current_page_lines = []

        if current_page_lines:
            self.full_content.append('\n'.join(current_page_lines))

        self.current_page = 0
        self.display_current_page()

    def display_current_page(self):
        if not self.full_content:
            self.output_text.delete("1.0", "end")
            self.page_label.configure(text="Page 0/0")
            self.prev_button.configure(state="disabled")
            self.next_button.configure(state="disabled")
            return

        total_pages = len(self.full_content)
        current_text = self.full_content[self.current_page]

        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", current_text)

        for i, line in enumerate(current_text.split('\n'), 1):
            line_lower = line.strip().lower()
            if line_lower.startswith("chapter") or line_lower.startswith("section") or line_lower.startswith("introduction") or line_lower.startswith("conclusion") or line_lower.lower().startswith("part"):
                self.output_text.tag_add("header", f"{i}.0", f"{i}.end")

        self.page_label.configure(text=f"Page {self.current_page + 1}/{total_pages}")
        self.prev_button.configure(state="disabled" if self.current_page == 0 else "normal")
        self.next_button.configure(state="disabled" if self.current_page == total_pages - 1 else "normal")

    def show_next_page(self):
        if self.current_page < len(self.full_content) - 1:
            self.current_page += 1
            self.display_current_page()

    def show_previous_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.display_current_page()

    # ------------------ GENERATION LOGIC (THREADED) ------------------

    def start_generation_thread(self):
        """يبدأ عملية التوليد في ثريد منفصل لتجنب تجميد الواجهة."""
        prompt = self.prompt_entry.get().strip()
        author_name = self.author_name_var.get().strip()

        if not self.client:
            messagebox.showerror("Error", "Please enter and validate your Gemini API Key first.")
            return
        if not prompt:
            messagebox.showerror("Error", "Please enter a topic/prompt for the book.")
            return
        if not author_name:
            messagebox.showerror("Error", "Please enter the Author's Name.")
            return

        self.output_text.delete("1.0", "end")
        self.full_content = []
        self.stream_buffer = ""
        self.token_count = 0
        
        self.progress_label.configure(text="Status: Generating Plan & Title...", text_color="orange")
        self.progress_bar.set(0)
        self.progress_bar.start()
        
        self.generate_button.configure(state="disabled", text="Generating...")
        self.save_txt_button.configure(state="disabled", fg_color="gray")
        self.trend_button.configure(state="disabled")
        self.update_idletasks()

        t = threading.Thread(target=self._run_generation_process)
        t.start()
        
    def _run_generation_process(self):
        """العملية الرئيسية لتوليد الكتاب (داخل الثريد)."""
        prompt = self.prompt_entry.get().strip()
        language = self.language_var.get()
        genre = self.genre_var.get()
        full_book_content = ""

        # 1. توليد الخطة والعنوان أولاً
        book_plan_and_title = get_book_plan(self.client, prompt, language, genre)

        if isinstance(book_plan_and_title, str) and (book_plan_and_title.startswith("API Error") or book_plan_and_title.startswith("An unexpected error")):
            self.after(0, lambda: self._handle_error("Plan Generation Failed", book_plan_and_title))
            return

        plan_lines = book_plan_and_title.split('\n')
        raw_title = plan_lines[0].strip() if plan_lines and plan_lines[0].strip() else "Generated Book Title"
        self.book_title = re.sub(r'^["\']|["\']$', '', raw_title).strip()
        
        # استخراج الملخص من الخطة 
        summary_start_index = 1
        summary_lines = []
        for i in range(summary_start_index, len(plan_lines)):
            line = plan_lines[i].strip()
            if not line:
                continue
            if line.lower().startswith(("table of contents", "محتويات", "chapters", "فصول", "part", "جزء")):
                break
            summary_lines.append(line)
        self.book_content_summary = ' '.join(summary_lines[:7]).strip() # زيادة الأسطر للملخص
        
        self.after(0, lambda: self.title(f"Gemini Masterpiece Creator 📝 - Book: {self.book_title[:40]}..."))
        
        # 1.5 توليد المحتوى التسويقي
        self.after(0, lambda: self.progress_label.configure(text=f"Status: Generating High-Quality Marketing Content...", text_color="purple"))
        
        marketing_data = generate_marketing_content(self.client, self.book_title, self.book_content_summary, language, genre)
        
        if isinstance(marketing_data, str) and not isinstance(marketing_data, dict):
            # معالجة الخطأ العام إذا لم يكن الناتج ديكشنري
            self.after(0, lambda: self._handle_error("Marketing Content Failed", marketing_data))
            return
            
        self.after(0, lambda: self._update_marketing_ui(marketing_data))


        # 2. بدء توليد المحتوى بشكل متدفق
        self.after(0, lambda: self.progress_label.configure(text=f"Status: Streaming Book Content (Title: {self.book_title[:30]}...)", text_color="yellow"))
        self.progress_bar.stop()
        
        response_stream = stream_book_content(self.client, book_plan_and_title, language, genre)

        if isinstance(response_stream, str) and (response_stream.startswith("API Error") or response_stream.startswith("An unexpected error")):
            self.after(0, lambda: self._handle_error("Content Streaming Failed", response_stream))
            return

        # 3. معالجة التدفق وعرضه
        try:
            for chunk in response_stream:
                if chunk.text:
                    full_book_content += chunk.text
                    self.stream_buffer += chunk.text
                    
                    self.token_count += len(chunk.text) / 4
                    progress_value = min(1.0, self.token_count / self.estimated_tokens)
                    self.after(0, lambda p=progress_value: self.progress_bar.set(p))
                    
                    if len(self.stream_buffer) > 100:
                        self.after(0, lambda t=self.stream_buffer: self._update_ui_stream(t))
                        self.stream_buffer = ""

        except Exception as e:
            error_message = f"Content stream interrupted or stopped unexpectedly: {e}"
            self.after(0, lambda: self._handle_completion(full_book_content, error_message, is_error=True))
            return

        # تحديث الواجهة بما تبقى في المخزن المؤقت
        if self.stream_buffer:
            self.after(0, lambda t=self.stream_buffer: self._update_ui_stream(t))

        # 4. اكتمال التوليد بنجاح
        self.after(0, lambda: self._handle_completion(full_book_content))

    def _update_ui_stream(self, text_chunk):
        """تحديث مربع النص تدريجياً."""
        self.output_text.insert(END, text_chunk)
        self.output_text.see(END)
        self.stream_buffer = ""
        
    def _update_marketing_ui(self, marketing_data):
        """تحديث حقول المحتوى التسويقي."""
        
        # Book Pitch
        self.pitch_box.configure(state="normal")
        self.pitch_box.delete("0.0", END)
        self.pitch_box.insert("0.0", marketing_data.get("pitch", "Pitch generation failed."))
        self.pitch_box.configure(state="disabled")

        # Hashtags
        self.hashtags_box.configure(state="normal")
        self.hashtags_box.delete("0.0", END)
        self.hashtags_box.insert("0.0", marketing_data.get("hashtags", "Hashtag generation failed."))
        self.hashtags_box.configure(state="disabled")

        # Cover Prompt
        self.cover_desc_box.configure(state="normal")
        self.cover_desc_box.delete("0.0", END)
        self.cover_desc_box.insert("0.0", marketing_data.get("cover_desc", "Cover Prompt generation failed."))
        self.cover_desc_box.configure(state="disabled")


    def _handle_error(self, title, message):
        """يعالج الأخطاء ويستعيد الواجهة."""
        messagebox.showerror(title, message)
        self.progress_label.configure(text="Status: Generation Failed", text_color="red")
        self.progress_bar.set(0)
        self.generate_button.configure(state="normal", text="Start Masterpiece Generation")
        self.trend_button.configure(state="normal")

    def _handle_completion(self, content, error_message=None, is_error=False):
        """يعالج اكتمال أو توقف التوليد (سواء بنجاح أو فشل)."""

        self.paginate_content(content)
        self.progress_bar.set(1.0)

        if is_error:
            self.progress_label.configure(text=f"Status: Stream Interrupted. Saved Partial Content.", text_color="red")
            messagebox.showwarning("Generation Incomplete", f"{error_message}\n\nSaving the partial content generated so far.")
        else:
            self.progress_label.configure(text=f"Status: Generation Complete. Saving PDF File...", text_color="blue")

        self.generate_button.configure(state="normal", text="Start Masterpiece Generation")
        self.trend_button.configure(state="normal")
        self.save_txt_button.configure(state="normal", fg_color="teal")

        if content.strip():
            self.save_book(self.prompt_entry.get().strip(), content, self.author_name_var.get().strip())
        else:
            messagebox.showwarning("No Content", "No content was generated or saved.")


    # ------------------ UTILITY METHODS ------------------
    def paste_from_clipboard(self, entry_widget):
        try:
            clipboard_content = self.clipboard_get()
            entry_widget.delete(0, 'end')
            entry_widget.insert(0, clipboard_content)
            if entry_widget == self.api_entry:
                self.initialize_client()
        except TclError:
            messagebox.showerror("Paste Error", "Could not access clipboard content. Please try manual input.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during paste: {e}")
            
    def copy_from_textbox(self, textbox_widget):
        """لصق محتوى Textbox في الحافظة."""
        try:
            content = textbox_widget.get("1.0", "end-1c") # الحصول على كل النص باستثناء السطر الأخير الفارغ
            if not content.strip():
                 messagebox.showwarning("Copy Failed", "The field is empty or contains no meaningful content to copy.")
                 return
                 
            self.clipboard_clear()
            self.clipboard_append(content)
            self.progress_label.configure(text="Status: Content copied to clipboard!", text_color="green")
        except Exception as e:
            messagebox.showerror("Copy Error", f"Could not copy content: {e}")


    def initialize_client(self, event=None):
        key = self.api_key.get()
        if key:
            try:
                self.client = genai.Client(api_key=key)
                self.progress_label.configure(text="Status: Gemini Client Ready (PRO Model used)", text_color="green")
                self.generate_button.configure(state="normal")
                self.trend_button.configure(state="normal")
            except Exception:
                self.progress_label.configure(text="Status: API Key Invalid/Error", text_color="red")
                self.generate_button.configure(state="disabled")
                self.trend_button.configure(state="disabled")
        else:
            self.progress_label.configure(text="Status: Enter API Key", text_color="yellow")
            self.generate_button.configure(state="disabled")
            self.trend_button.configure(state="disabled")

    def find_trending_topics(self):
        """يبحث عن المواضيع الرائجة ويبدأ نافذة TopicSelector."""
        if not self.client:
            messagebox.showerror("Error", "Please enter and validate your Gemini API Key first.")
            return

        genre = self.genre_var.get()
        language = self.language_var.get()

        self.progress_label.configure(text=f"Status: Searching for Trending Topics in '{genre}'...", text_color="orange")
        self.progress_bar.start()
        self.update_idletasks()

        def search_thread():
            trending_topics = get_trending_topics(self.client, genre, language)
            self.after(0, lambda: self._handle_topic_search_result(trending_topics, genre))
            
        threading.Thread(target=search_thread).start()

    def _handle_topic_search_result(self, trending_topics, genre):
        """يعالج نتائج البحث عن المواضيع."""
        self.progress_bar.stop()
        self.progress_label.configure(text="Status: Ready to Generate", text_color="green")

        if isinstance(trending_topics, str):
            messagebox.showerror("Search Failed", trending_topics)
            return

        if not trending_topics:
            messagebox.showinfo("Search Result", f"Could not find trending topics for '{genre}' at this moment.")
            return

        TopicSelector(
            master=self,
            topics=trending_topics,
            prompt_entry_widget=self.prompt_entry,
            progress_label_widget=self.progress_label,
            genre=genre
        )


    def save_book_txt(self):
        """حفظ المحتوى كاملاً كملف نصي عادي (.txt)."""
        if not self.full_content:
            messagebox.showerror("Error", "No content to save. Please generate the book first.")
            return

        content = '\n'.join(self.full_content)

        filename = self.book_title.replace(" ", "_").replace("'", "").replace(":", "")[:30] + "_book.txt"

        try:
            save_dir = "/sdcard/Download"
            if not os.path.exists(save_dir):
                save_dir = os.path.join(os.path.expanduser("~"), "Download")
        except Exception:
            save_dir = os.getcwd()

        save_path = os.path.join(save_dir, filename)

        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(content)

            self.progress_label.configure(text=f"Status: TXT Saved to {save_path}", text_color="green")
            messagebox.showinfo("Success", f"Book saved successfully as a Text File! 💾\nFile: {filename}\nLocation: {save_dir}")

        except Exception as e:
            self.progress_label.configure(text="Status: TXT Save Failed!", text_color="red")
            messagebox.showerror("Save Error", f"Could not save the TXT file: {e}\n(The problem might be storage permissions).")


    def save_book(self, prompt, content, author_name):
        """
        إنشاء وحفظ المحتوى بصيغة PDF بالتصميم الاحترافي الجديد.
        (تم الإبقاء على منطق PDF كما هو لضمان تنسيق الجزء والفصل كما طُلِب مسبقاً)
        """

        book_title = self.book_title
        filename = book_title.replace(" ", "_").replace("'", "").replace(":", "")[:30] + "_masterpiece.pdf"
        
        content_font = NORMAL_FONT_NAME
        header_font = BOLD_FONT_NAME
        
        try:
            save_dir = "/sdcard/Download"
            if not os.path.exists(save_dir):
                save_dir = os.path.join(os.path.expanduser("~"), "Download")
        except Exception:
            save_dir = os.getcwd()

        save_path = os.path.join(save_dir, filename)

        try:
            # 💡 1. إعداد المستند
            doc = SimpleDocTemplate(
                save_path,
                pagesize=A4,
                leftMargin=72,
                rightMargin=72,
                topMargin=72,
                bottomMargin=72
            )
            styles = getSampleStyleSheet()
            story = []
            
            # 💡 2. إعداد الأنماط (التي تم تأكيدها في التحديث السابق)
            NormalStyle = ParagraphStyle(
                'BodyText',
                parent=styles['Normal'],
                fontName=content_font,
                fontSize=FONT_SIZE,
                leading=FONT_SIZE * 1.6,
                spaceAfter=12,
                alignment=TA_JUSTIFY,
            )

            # 🛑 نمط عنوان الفصل (Chapter): صغير وبارز في الأعلى 
            ChapterStyle = ParagraphStyle(
                'ChapterHeader',
                parent=styles['Heading1'],
                fontName=header_font, 
                fontSize=FONT_SIZE + 6,
                leading=FONT_SIZE * 2,
                spaceBefore=0,
                spaceAfter=15,
                alignment=TA_CENTER
            )
            
            # 🛑 النمط الجديد لـ رقم الجزء (Part X): ضخم جداً 60 نقطة (في المنتصف)
            BigPartTitleStyle = ParagraphStyle(
                'BigPartTitle',
                parent=styles['Heading1'],
                fontName=BOLD_FONT_NAME,
                fontSize=60,
                leading=72,
                alignment=TA_CENTER,
                textColor='#000000'
            )
            
            # 🛑 النمط الجديد لـ عنوان الجزء: كبير جداً 48 نقطة (في المنتصف)
            PartTopicStyle = ParagraphStyle(
                'PartTopicTitle',
                parent=styles['Heading1'],
                fontName=BOLD_FONT_NAME,
                fontSize=48,
                leading=58,
                alignment=TA_CENTER,
                textColor='#333333',
                spaceBefore=30
            )
            
            # 🛑 3. إنشاء صفحة الغلاف (Cover Page)
            story.append(Spacer(1, doc.height / 4))

            CoverTitleStyle = ParagraphStyle(
                'CoverTitle',
                parent=styles['Heading1'],
                fontName=header_font,
                fontSize=36,
                leading=45,
                spaceAfter=50,
                alignment=TA_CENTER
            )
            story.append(Paragraph(book_title, CoverTitleStyle))

            AuthorStyle = ParagraphStyle(
                'Author',
                parent=styles['Normal'],
                fontName=content_font,
                fontSize=20,
                spaceBefore=100,
                alignment=TA_CENTER
            )
            story.append(Paragraph(f"By {author_name}", AuthorStyle))

            story.append(PageBreak())
            
            
            # 🛑 4. تحليل المحتوى وتطبيق الأنماط (المنطق الذي تم تثبيته مسبقاً)
            content_lines = content.split('\n')
            
            if content_lines and re.sub(r'^["\']|["\']$', '', content_lines[0].strip()).strip() == book_title:
                content_lines = content_lines[1:]
                
            current_group = []
            part_number_line = None 
            
            for line in content_lines:
                line_lower = line.strip()
                if not line_lower:
                    continue

                is_part = line_lower.lower().startswith(("part", "الجزء"))
                is_chapter = line_lower.lower().startswith(("chapter", "chapitre", "الفصل"))
                is_intro_conc = line_lower.lower().startswith(("introduction", "conclusion", "مقدمة", "خاتمة"))
                is_section = re.match(r'^\d+\.\d+\.?\s|^[ا-ي]\.\s|^section\s', line_lower.lower())
                
                
                # 🛑 معالجة الجزء (Part): صفحة مستقلة في المنتصف
                if is_part:
                    
                    if current_group:
                        story.extend(current_group)
                        current_group = []
                        
                    if story:
                        story.append(PageBreak())
                    
                    part_number_line = line_lower
                    continue

                # 🛑 معالجة عنوان الجزء (السطر الذي يلي "الجزء X" مباشرة)
                elif part_number_line is not None:
                    
                    story.append(Spacer(1, doc.height / 5)) 
                    story.append(Paragraph(part_number_line, BigPartTitleStyle))
                    story.append(Paragraph(line_lower, PartTopicStyle))
                    
                    part_number_line = None
                    story.append(PageBreak())
                    continue


                # 🛑 معالجة الفصل (Chapter): صفحة مستقلة في الأعلى
                elif is_chapter or is_intro_conc:
                    
                    if current_group:
                        story.extend(current_group)
                        current_group = []
                        
                    if story:
                        story.append(PageBreak())
                    
                    story.append(Paragraph(line_lower, ChapterStyle))
                    story.append(Spacer(1, 24))
                    
                    continue

                # معالجة العناوين الفرعية
                elif is_section:
                    if current_group:
                        story.extend(current_group)
                        current_group = []

                    SubHeaderStyle = ParagraphStyle(
                        'SubHeader',
                        parent=styles['Heading2'],
                        fontName=header_font,
                        fontSize=FONT_SIZE + 2,
                        leading=FONT_SIZE * 1.5,
                        spaceBefore=15,
                        spaceAfter=8,
                        alignment=TA_JUSTIFY,
                    )
                    story.append(Paragraph(line_lower, SubHeaderStyle))
                    
                # معالجة الفقرات العادية
                else:
                    para = Paragraph(line_lower, NormalStyle)
                    current_group.append(para)

            # إضافة أي محتوى متبقي
            if current_group:
                story.extend(current_group)
            
            
            # 🛑 5. بناء مستند PDF
            doc.build(story, onFirstPage=lambda canvas, doc: my_on_each_page(canvas, doc, book_title),
                      onLaterPages=lambda canvas, doc: my_on_each_page(canvas, doc, book_title))

            self.progress_label.configure(text=f"Status: PDF Saved to {save_path}", text_color="green")
            messagebox.showinfo("Success", f"Book saved successfully as a PDF! 💾\nFile: {filename}\nLocation: {save_dir}")

        except Exception as e:
            self.progress_label.configure(text="Status: PDF Save Failed!", text_color="red")
            messagebox.showerror("Save Error", f"Could not save the PDF file: {e}\n(The problem might be due to fonts or storage permissions).")


if __name__ == "__main__":
    app = BookWriterApp()
    app.mainloop()
