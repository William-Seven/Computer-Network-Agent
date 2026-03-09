from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from pypdf import PdfReader
import os
import uuid

class MultimodalPDFLoader(PyPDFLoader):
    """
    增强版 PDF 加载器：同时提取文本和图片
    """
    def __init__(self, file_path: str, image_output_dir: str = "data/assets"):
        super().__init__(file_path)
        self.image_output_dir = image_output_dir
        os.makedirs(image_output_dir, exist_ok=True)
        
        # 定义全局配置：只有在下面列表中的文件才会提取图片并参与多模态
        self.WHITELIST_PDFS_FOR_IMAGES = [
            "实验三报告.pdf",
            "实验四报告.pdf"
        ]

    def lazy_load(self):
        """惰性加载 PDF，提取文本并在对应位置插入图片标记"""
        try:
            # 显式打印，确认方法被调用
            print(f"📖 Processing PDF: {self.file_path}")
            reader = PdfReader(self.file_path)
            
            # 判断当前 PDF 是否在白名单中
            base_name = os.path.basename(self.file_path)
            should_extract_images = False
            for allowed in self.WHITELIST_PDFS_FOR_IMAGES:
                if allowed in base_name:
                    should_extract_images = True
                    break
            
            if not self.WHITELIST_PDFS_FOR_IMAGES: 
                # 这里如果你想默认什么都不提取，就设为False，或者你想默认提取指定的可以修改这里
                pass
                
            if should_extract_images:
                print(f"  ✨ PDF '{base_name}' 在图片提取白名单中，将进行图片解析。")
            else:
                print(f"  ⏭️ PDF '{base_name}' 不在白名单中，跳过所有图片提取逻辑。")

            for i, page in enumerate(reader.pages):
                # 1. 提取文本
                text = page.extract_text() or ""
                
                # 2. 提取图片
                image_tags = []
                if should_extract_images and hasattr(page, "images"):
                    try:
                        # 注意：page.images 是一个属性，访问它会触发提取过程
                        images = page.images
                        if images:
                            print(f"  - Page {i+1}: Found {len(images)} images.")
                            for image_file_object in images:
                                try:
                                    # 生成唯一文件名
                                    img_ext = os.path.splitext(image_file_object.name)[1] or ".jpg"
                                    img_filename = f"pdf_{uuid.uuid4().hex[:8]}{img_ext}"
                                    
                                    # 确保使用绝对路径以避免多线程/CWD 问题
                                    abs_output_dir = os.path.abspath(self.image_output_dir)
                                    # 存储用的相对路径（为了以后迁移/展示方便）
                                    img_rel_path = os.path.join(self.image_output_dir, img_filename)
                                    # 写入用的绝对路径
                                    abs_img_path = os.path.join(abs_output_dir, img_filename)

                                    # 保存图片
                                    with open(abs_img_path, "wb") as f:
                                        f.write(image_file_object.data)
                                    
                                    # 只有成功读取并保存，才作为有效地视觉标签记录
                                    image_tags.append(f"image:{img_rel_path}")
                                except Exception:
                                    # 跳过无法识别的图片格式，不考虑向量化
                                    pass
                        else:
                            pass 
                    except Exception:
                         # 跳过无法访问 images 属性的页面 (如 jbig2dec 报错)
                         pass
                
                # 3. 组合内容：文本 + 图片标记
                if image_tags:
                    text += "\n\n" + "\n".join(image_tags)
                
                metadata = {"source": self.file_path, "page": i + 1}
                yield Document(page_content=text, metadata=metadata)
            
        except Exception as e:
            print(f"❌ PDF 加载失败 {self.file_path}: {e}")
            return

    def load(self):
        return list(self.lazy_load())