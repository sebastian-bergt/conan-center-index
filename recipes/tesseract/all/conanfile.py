import os
from conans import ConanFile, CMake, tools
from conans.errors import ConanInvalidConfiguration


class TesseractConan(ConanFile):
    name = "tesseract"
    description = "Tesseract Open Source OCR Engine"
    url = "https://github.com/conan-io/conan-center-index"
    topics = ("conan", "ocr", "image", "multimedia", "graphics")
    license = "Apache-2.0"
    homepage = "https://github.com/tesseract-ocr/tesseract"
    exports_sources = ["CMakeLists.txt"]
    generators = "cmake", "cmake_find_package"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False],
               "fPIC": [True, False],
               "with_training": [True, False]}
    default_options = {'shared': False, 'fPIC': True, 'with_training': False}
    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"
    _cmake = None

    requires = "leptonica/1.79.0"

    def source(self):
        tools.get(**self.conan_data["sources"][self.version])
        extracted_dir = self.name + "-" + self.version
        os.rename(extracted_dir, self._source_subfolder)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.options.with_training:
            # do not enforce failure and allow user to build with system cairo, pango, fontconfig
            self.output.warn("*** Build with training is not yet supported, continue on your own")

    def configure(self):
        # Exclude old compilers not supported by tesseract
        compiler_version = tools.Version(self.settings.compiler.version)
        if (self.settings.compiler == "gcc" and compiler_version < "5") or \
                (self.settings.compiler == "clang" and compiler_version < "5"):
            raise ConanInvalidConfiguration("tesseract/{} requires Clang >= 5".format(self.version))

    def _configure_cmake(self):
        if self._cmake:
            return self._cmake
        cmake = self._cmake = CMake(self)
        cmake.definitions['BUILD_TRAINING_TOOLS'] = self.options.with_training
        cmake.definitions["STATIC"] = not self.options.shared
        # Use CMake-based package build and dependency detection, not the pkg-config, cppan or SW
        cmake.definitions['CPPAN_BUILD'] = False
        cmake.definitions['SW_BUILD'] = False

        # avoid accidentally picking up system libarchive
        cmake.definitions['CMAKE_DISABLE_FIND_PACKAGE_LIBARCHIVE'] = True

        # Set Leptonica_DIR to ensure that find_package will be called in original CMake file
        cmake.definitions['Leptonica_DIR'] = self.deps_cpp_info['leptonica'].rootpath

        cmake.configure(build_folder=self._build_subfolder)
        return cmake

    def _patch_sources(self):
        # Use generated cmake module files
        tools.replace_in_file(
            os.path.join(self._source_subfolder, "CMakeLists.txt"),
            "find_package(Leptonica ${MINIMUM_LEPTONICA_VERSION} REQUIRED CONFIG)",
            "find_package(Leptonica ${MINIMUM_LEPTONICA_VERSION} REQUIRED)")
        # Variable Leptonica_LIBRARIES does not know about its dependencies which are handled only
        # by exported cmake/pc files which are not used by Conan.
        # Therefore link with exported target from the autogenerated CMake file by the cmake_find_package
        # that contains information about all dependencies
        tools.replace_in_file(
            os.path.join(self._source_subfolder, "CMakeLists.txt"),
            "${Leptonica_LIBRARIES}",
            "Leptonica::Leptonica")

    def build(self):
        self._patch_sources()
        cmake = self._configure_cmake()
        cmake.build()

    def package(self):
        cmake = self._configure_cmake()
        cmake.install()

        self.copy("LICENSE", src=self._source_subfolder, dst="licenses")
        # remove man pages
        tools.rmdir(os.path.join(self.package_folder, 'share', 'man'))
        # remove pkgconfig
        tools.rmdir(os.path.join(self.package_folder, 'lib', 'pkgconfig'))
        # remove cmake
        tools.rmdir(os.path.join(self.package_folder, 'cmake'))

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)
        if self.settings.os == "Linux":
            self.cpp_info.system_libs = ["pthread"]
        elif self.settings.compiler == "Visual Studio":
            if not self.options.shared:
                self.cpp_info.system_libs = ["ws2_32"]
        self.cpp_info.names["cmake_find_package"] = "Tesseract"
        self.cpp_info.names["cmake_find_package_multi"] = "Tesseract"