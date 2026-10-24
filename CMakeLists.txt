cmake_minimum_required(VERSION 3.21)

project(Demon VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_INCLUDE_CURRENT_DIR ON)

find_package(Qt6 6.8 REQUIRED COMPONENTS Core Network Widgets Multimedia)

# 源文件列表（后续模块直接往这里加）
set(DEMON_SOURCES
    src/main.cpp
    src/app/demon.rc
    src/app/AppController.cpp
    src/app/AppController.h
    src/config/Config.cpp
    src/config/Config.h
    src/http/HttpServer.cpp
    src/http/HttpServer.h
    src/util/Log.cpp
    src/util/Log.h
    src/ui/MainWindow.cpp
    src/ui/MainWindow.h
    src/util/TextSplit.cpp
    src/util/TextSplit.h
    src/voice/TtsClient.cpp
    src/voice/TtsClient.h
    src/voice/AudioPlayer.cpp
    src/voice/AudioPlayer.h
)

# 开发时用控制台方便看日志；发布版关掉控制台（日志仍写文件）
option(DEMON_CONSOLE "Build with console window for development" OFF)

if (DEMON_CONSOLE)
    add_executable(demon ${DEMON_SOURCES})
else()
    add_executable(demon WIN32 ${DEMON_SOURCES})
endif()

# 让 "config/Config.h" 这类包含路径生效
target_include_directories(demon PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src)

target_link_libraries(demon PRIVATE
    Qt6::Core
    Qt6::Network
    Qt6::Widgets
    Qt6::Multimedia
)

if (MSVC)
    # 源码里有中文注释与中文字面量，必须显式 UTF-8
    target_compile_options(demon PRIVATE /utf-8 /W3)
endif()

# 输出到 build/bin，方便 windeployqt
set_target_properties(demon PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
)
