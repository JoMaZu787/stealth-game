import pyglet as pg


vertex_source = """#version 150 core
    in vec2 position;
    in vec4 colors;
    out vec4 vertex_colors;

    uniform mat4 projection;

    void main()
    {
        gl_Position = projection * vec4(position, 0.0, 1.0);
        vertex_colors = colors;
    }
"""

fragment_source = """#version 150 core
    in vec4 vertex_colors;
    out vec4 final_color;

    void main()
    {
        final_color = vertex_colors;
    }
"""

vert_shader = pg.graphics.shader.Shader(vertex_source, 'vertex')
frag_shader = pg.graphics.shader.Shader(fragment_source, 'fragment')
program = pg.graphics.shader.ShaderProgram(vert_shader, frag_shader)

window = pg.window.Window()
circle = pg.shapes.Circle(window.width/2, window.height/2, 20)


