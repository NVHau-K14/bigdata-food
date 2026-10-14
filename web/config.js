/**
 * Cấu hình thông tin nhóm và dự án cho Dashboard.
 * Để trống theo quy định để nhóm tự điền thông tin chính thức, không tự ý bịa tên.
 */
window.APP_CONFIG = {
  projectTitle: "Phân tích hành vi ăn uống và gợi ý món ăn",
  courseName: "Nhập môn Big Data",
  institution: "",       // Tên trường đại học (nhóm tự điền)
  classGroup: "",        // Tên lớp / Nhóm học phần (nhóm tự điền)
  instructor: "",        // Tên giảng viên hướng dẫn (nhóm tự điền)
  members: [
    { name: "", studentId: "", role: "" },
    { name: "", studentId: "", role: "" }
  ],
  academicYear: "2026",
  defaultDataset: "vifoodrec" // "vifoodrec" hoặc "food_com"
};
